"""Document ingestion service — orchestrates upload processing pipeline.

Pipeline statuses:
  uploaded → stored → text_extracted → items_detected → classification_pending → processed
  → failed (if any step errors)
  → duplicate_detected (if hash match found)
  → needs_review (if OCR fails or returns empty)

Real OCR is performed via the dispatch layer:
  - PDFs: pdfplumber → tesseract fallback for scans
  - Images: tesseract directly
  - Text files: identity pass-through
"""
import hashlib
from datetime import datetime, timezone
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.document import Document
from app.models.tax_item import TaxItem
from app.models.document_item import DocumentItem
from app.models.document_page import DocumentPage
from app.services.audit.writer import write_audit
from app.ocr.dispatch import extract_text
from app.config import settings
from app.repositories.job_repo import JobRepository


@dataclass
class UploadResult:
    """Result of the upload pipeline."""
    document: Document
    duplicate_of: str | None = None


async def process_upload(
    db: AsyncSession,
    document_id: str,
    job_id: str,
    session_id: str,
    original_filename: str,
    mime_type: str,
    file_data: bytes,
    category: str | None = None,
    financial_year: str | None = None,
) -> UploadResult:
    """Run the ingestion pipeline for an uploaded file.

    Called from the background task after the document record is created.

    1. Fetch the pre-created document record
    2. Check for duplicates in the same session
    3. Run OCR pipeline
    4. Update job progress throughout
    """
    job_repo = JobRepository(db)

    # Fetch the document that was created by the upload endpoint
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise ValueError(f"Document {document_id} not found")

    # Mark job as running
    await job_repo.update_status(job_id, "running", progress=0.0)

    # Compute hash
    file_hash = hashlib.sha256(file_data).hexdigest()
    doc.file_hash = file_hash

    # Check for duplicate by hash in same session
    duplicate = await _check_hash_duplicate(db, session_id, file_hash, document_id)

    # Update document status based on dedup check
    status = "duplicate_detected" if duplicate else "stored"
    status_reason = None
    if duplicate:
        status_reason = (
            f"Duplicate detected — file hash matches existing document "
            f"{duplicate.id} ({duplicate.original_filename})"
        )

    doc.status = status
    doc.status_reason = status_reason
    await db.flush()
    await write_audit(
        db, "document", doc.id, "uploaded",
        details={
            "filename": original_filename,
            "size": len(file_data),
            "hash": file_hash,
            "duplicate": bool(duplicate),
            "duplicate_of": duplicate.id if duplicate else None,
        },
    )

    # Update job: hash check complete
    await job_repo.update_status(job_id, "running", progress=0.2,
                                 progress_message="Hash check complete")

    # Run pipeline steps (OCR + processing)
    if not duplicate:
        await _run_ocr_pipeline(db, doc, file_data, mime_type, job_repo, job_id)
    else:
        # Job succeeded immediately (duplicate — no processing needed)
        await job_repo.update_status(job_id, "succeeded", progress=1.0,
                                     progress_message="Duplicate detected — no processing needed",
                                     result_summary=f"Duplicate of {duplicate.id}")

    await db.commit()
    await db.refresh(doc)
    return UploadResult(
        document=doc,
        duplicate_of=duplicate.id if duplicate else None,
    )


async def _check_hash_duplicate(
    db: AsyncSession, session_id: str, file_hash: str, exclude_document_id: str | None = None
) -> Document | None:
    """Return existing document if same file hash already exists in this session."""
    stmt = select(Document).where(
        Document.session_id == session_id,
        Document.file_hash == file_hash,
    )
    if exclude_document_id:
        stmt = stmt.where(Document.id != exclude_document_id)
    result = await db.execute(stmt)
    return result.scalars().first()


async def _run_ocr_pipeline(
    db: AsyncSession,
    doc: Document,
    file_data: bytes,
    mime_type: str,
    job_repo: JobRepository,
    job_id: str,
) -> None:
    """Run the real OCR pipeline — extract text, store pages, update status.

    Steps:
    1. text_extracted — run OCR via dispatch (pdfplumber/tesseract/identity)
    2. Store per-page results in document_pages
    3. items_detected — placeholder (future: auto-detect line items from text)
    4. classification_pending — placeholder (future: auto-classify)
    5. processed

    If OCR returns empty text, mark as needs_review instead of processed.
    """
    # Step 1-2: OCR extraction
    doc.status = "text_extracted"
    await db.flush()
    await job_repo.update_status(job_id, "running", progress=0.4,
                                 progress_message="Extracting text...")

    ocr_result = await extract_text(file_data, mime_type)

    # Store per-page results
    for page in ocr_result.pages:
        page_record = DocumentPage(
            document_id=doc.id,
            page_number=page.page_number,
            text=page.text,
            confidence=page.confidence,
            ocr_method=ocr_result.method,
        )
        db.add(page_record)

    await db.flush()
    await write_audit(db, "document", doc.id, "text_extracted",
                      details={
                          "method": ocr_result.method,
                          "pages": len(ocr_result.pages),
                          "total_chars": len(ocr_result.full_text),
                      })

    await job_repo.update_status(job_id, "running", progress=0.6,
                                 progress_message=f"OCR complete: {len(ocr_result.pages)} pages")

    # If OCR returned no text, flag for review
    if not ocr_result.full_text.strip():
        doc.status = "needs_review"
        doc.status_reason = "OCR returned no text — document may be unreadable."
        await db.flush()
        await write_audit(db, "document", doc.id, "needs_review",
                          details={"reason": "OCR returned empty text"})
        await job_repo.update_status(job_id, "succeeded", progress=1.0,
                                     progress_message="OCR returned no text — needs review",
                                     result_summary="{\"status\": \"needs_review\", \"reason\": \"empty_ocr\"}")
        return

    # Step 3: items_detected — text is ready for classification
    doc.status = "items_detected"
    await db.flush()
    await write_audit(db, "document", doc.id, "items_detected",
                      details={"extracted_text_hash": hashlib.sha256(ocr_result.full_text.encode()).hexdigest()})
    await job_repo.update_status(job_id, "running", progress=0.8,
                                 progress_message="Text extracted — running classification...")

    # Step 4: auto-classify the extracted text using the configured AI provider
    await _run_classification(
        db, doc, ocr_result.full_text, job_repo, job_id,
    )


async def _run_classification(
    db: AsyncSession,
    doc: Document,
    text: str,
    job_repo: JobRepository,
    job_id: str,
) -> None:
    """Run the configured AI provider to classify extracted text.

    Creates a TaxItem record and links it to the source document.
    On failure, marks document as classification_failed.
    """
    from app.services.classification import classify_document
    from app.models.tax_session import TaxSession

    await job_repo.update_status(job_id, "running", progress=0.9,
                                 progress_message="Classification in progress...")

    try:
        fy = doc.financial_year
        if not fy:
            sess_result = await db.execute(
                select(TaxSession).where(TaxSession.id == doc.session_id)
            )
            session_row = sess_result.scalar_one_or_none()
            fy = session_row.financial_year if session_row else "2025-2026"

        # Run classification — creates TaxItem and DocumentItem links
        items = await classify_document(
            db=db,
            document_id=doc.id,
            session_id=doc.session_id,
            extracted_text=text,
            financial_year=fy,
            skill_context="Auto-classified from OCR pipeline.",
        )

        doc.status = "classified"
        doc.status_reason = None
        await db.flush()
        first_item = items[0] if items else None
        await write_audit(db, "document", doc.id, "classified",
                          details={
                              "item_count": len(items),
                              "first_item_id": first_item.id if first_item else None,
                              "first_category": first_item.category if first_item else None,
                              "first_confidence": first_item.confidence if first_item else None,
                              "needs_review": any(i.needs_review for i in items),
                          })

        await job_repo.update_status(job_id, "succeeded", progress=1.0,
                                     progress_message=f"{len(items)} items classified",
                                     result_summary=f'{{"status": "classified", "item_count": {len(items)}, "first_item_id": "{first_item.id if first_item else ""}", "first_category": "{first_item.category if first_item else ""}"}}')

    except Exception as exc:
        doc.status = "classification_failed"
        doc.status_reason = f"{type(exc).__name__}: {exc}"
        await db.flush()
        await write_audit(db, "document", doc.id, "classification_failed",
                          details={"error": str(exc)})
        await job_repo.update_status(job_id, "failed", progress=None,
                                     error_message=f"Classification failed: {exc}",
                                     result_summary='{"status": "classification_failed"}')
        raise  # Re-raise so run_job_sync catches it and doesn't overwrite with "succeeded"
