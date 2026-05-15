"""CRUD routes for documents — including file upload endpoint."""
import os
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.db.deps import get_db
from app.models.document import Document
from app.models.document_page import DocumentPage
from app.schemas.document import (
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse,
    DocumentPageResponse,
    DocumentUploadResponse,
)
from app.schemas.job import JobResponse
from app.services.audit.writer import write_audit
from app.services.ingestion.pipeline import process_upload
from app.services.job import create_job

router = APIRouter(prefix="/api/documents", tags=["documents"])

# MIME types and extensions allowed for upload
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/tiff",
}
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif"}


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(data: DocumentCreate, db: AsyncSession = Depends(get_db)):
    """Create a document record (metadata only — use /upload for file upload)."""
    document = Document(**data.model_dump())
    db.add(document)
    await db.flush()
    await write_audit(db, "document", document.id, "created")
    await db.commit()
    await db.refresh(document)
    return document


@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    session_id: str = Form(...),
    file: UploadFile = File(...),
    category: str | None = Form(default=None),
    financial_year: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a document file.

    - Stores file metadata
    - Computes SHA-256 hash for deduplication
    - Creates a queued ingestion job
    - Returns the job ID for status polling

    The ingestion pipeline (OCR, classification) runs as a background task.
    Poll `GET /api/jobs/{job_id}/status` to check progress.
    """
    # Read file bytes
    file_data = await file.read()
    if not file_data:
        raise HTTPException(status_code=400, detail="Empty file")

    # Validate file type
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS and file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext or file.content_type}. "
                   f"Allowed: PDF, PNG, JPG, TIFF",
        )

    # Validate file size (configurable via MAX_UPLOAD_SIZE_MB, default 20MB)
    max_size = getattr(settings, "max_upload_size_mb", 20) * 1024 * 1024
    if len(file_data) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large ({len(file_data) / 1024 / 1024:.1f} MB). "
                   f"Maximum: {max_size / 1024 / 1024:.0f} MB",
        )

    # Create initial document record with minimal metadata
    import hashlib
    file_hash = hashlib.sha256(file_data).hexdigest()

    doc = Document(
        session_id=session_id,
        original_filename=file.filename or "unknown",
        mime_type=file.content_type or "application/octet-stream",
        file_size_bytes=len(file_data),
        file_hash=file_hash,
        status="uploaded",
        category=category,
        financial_year=financial_year,
    )
    db.add(doc)
    await db.flush()
    await write_audit(db, "document", doc.id, "uploaded",
                      details={"filename": file.filename, "size": len(file_data)})

    # Create a queued ingestion job
    job = await create_job(
        db=db,
        session_id=session_id,
        document_id=doc.id,
        job_type="ingestion",
    )

    await db.commit()

    # Schedule the pipeline as a background task
    background_tasks.add_task(
        _run_ingestion_pipeline,
        document_id=doc.id,
        job_id=job["id"],
        file_data=file_data,
        session_id=session_id,
        original_filename=file.filename or "unknown",
        mime_type=file.content_type or "application/octet-stream",
        category=category,
        financial_year=financial_year,
    )

    return {
        "document_id": doc.id,
        "job_id": job["id"],
        "job_type": "ingestion",
        "job_status": "queued",
        "message": "Document uploaded. Ingestion pipeline queued.",
    }


@router.post("/upload/batch", status_code=status.HTTP_202_ACCEPTED)
async def upload_documents_batch(
    background_tasks: BackgroundTasks,
    session_id: str = Form(...),
    files: list[UploadFile] = File(...),
    category: str | None = Form(default=None),
    financial_year: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Upload multiple document files at once.

    Each file is processed independently — same validation and pipeline as single upload.
    Returns a list of results, each with document_id and job_id.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    if len(files) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 files per batch upload")

    results = []
    for file in files:
        file_data = await file.read()
        if not file_data:
            continue  # skip empty files

        # Validate file type
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in ALLOWED_EXTENSIONS and file.content_type not in ALLOWED_MIME_TYPES:
            continue  # skip unsupported types

        # Validate file size
        max_size = getattr(settings, "max_upload_size_mb", 20) * 1024 * 1024
        if len(file_data) > max_size:
            continue  # skip oversized files

        import hashlib
        file_hash = hashlib.sha256(file_data).hexdigest()

        doc = Document(
            session_id=session_id,
            original_filename=file.filename or "unknown",
            mime_type=file.content_type or "application/octet-stream",
            file_size_bytes=len(file_data),
            file_hash=file_hash,
            status="uploaded",
            category=category,
            financial_year=financial_year,
        )
        db.add(doc)
        await db.flush()
        await write_audit(db, "document", doc.id, "uploaded",
                          details={"filename": file.filename, "size": len(file_data)})

        job = await create_job(
            db=db,
            session_id=session_id,
            document_id=doc.id,
            job_type="ingestion",
        )

        background_tasks.add_task(
            _run_ingestion_pipeline,
            document_id=doc.id,
            job_id=job["id"],
            file_data=file_data,
            session_id=session_id,
            original_filename=file.filename or "unknown",
            mime_type=file.content_type or "application/octet-stream",
            category=category,
            financial_year=financial_year,
        )

        results.append({
            "document_id": doc.id,
            "job_id": job["id"],
            "filename": file.filename or "unknown",
            "job_type": "ingestion",
            "job_status": "queued",
            "message": "Document queued for ingestion.",
        })

    await db.commit()

    return {
        "total": len(results),
        "skipped": len(files) - len(results),
        "documents": results,
    }


async def _run_ingestion_pipeline(
    document_id: str,
    job_id: str,
    file_data: bytes,
    session_id: str,
    original_filename: str,
    mime_type: str,
    category: str | None = None,
    financial_year: str | None = None,
):
    """Run the ingestion pipeline as a background task.

    This function runs outside the request-response cycle, so it gets its own
    database session and manages its own lifecycle.

    Note: There is no asyncio timeout wrapping this function. Long-running
    pipelines (e.g. large PDF OCR) could theoretically run indefinitely.
    Processing timeout can be configured via `settings.processing_timeout_seconds`
    (default: 300s). To enforce, wrap the `run_job_sync` call with
    `asyncio.wait_for(pipeline_fn(), timeout=settings.processing_timeout_seconds)`.
    """
    from app.db.session import async_session_factory
    from app.services.ingestion.pipeline import process_upload
    from app.services.job import run_job_sync
    from app.config import settings

    import asyncio
    import logging
    logger = logging.getLogger(__name__)

    try:
        async with async_session_factory() as db:
            async def pipeline_fn():
                """Inner function that the job runner wraps with status tracking."""
                timeout = getattr(settings, "processing_timeout_seconds", 300)
                result = await asyncio.wait_for(
                    process_upload(
                        db=db,
                        document_id=document_id,
                        job_id=job_id,
                        session_id=session_id,
                        original_filename=original_filename,
                        mime_type=mime_type,
                        file_data=file_data,
                        category=category,
                        financial_year=financial_year,
                    ),
                    timeout=timeout,
                )
                await db.commit()
                return {
                    "document_id": result.document.id,
                    "status": result.document.status,
                    "duplicate_of": result.duplicate_of,
                }

            await run_job_sync(db, job_id, pipeline_fn)
            await db.commit()
    except asyncio.TimeoutError:
        logger.error(
            "Ingestion pipeline timed out after %ss for doc %s",
            getattr(settings, "processing_timeout_seconds", 300),
            document_id,
        )
    except Exception:
        logger.exception("Ingestion pipeline background task failed")


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    session_id: str | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Document)
        .order_by(Document.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    if session_id:
        stmt = stmt.where(Document.session_id == session_id)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.patch("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: str, data: DocumentUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(doc, field, value)
    await db.flush()
    await write_audit(db, "document", document_id, "updated",
                      details={"fields": list(update_data.keys())})
    await db.commit()
    await db.refresh(doc)
    return doc


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    await db.execute(delete(Document).where(Document.id == document_id))
    await write_audit(db, "document", document_id, "deleted")
    await db.commit()


@router.get("/{document_id}/pages", response_model=list[DocumentPageResponse])
async def get_document_pages(document_id: str, db: AsyncSession = Depends(get_db)):
    """Return all OCR pages for a given document, ordered by page number."""
    # Verify the document exists
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Query pages ordered by page_number
    stmt = (
        select(DocumentPage)
        .where(DocumentPage.document_id == document_id)
        .order_by(DocumentPage.page_number)
    )
    result = await db.execute(stmt)
    return result.scalars().all()
