import hashlib

from sqlalchemy import select

from app.models.document import Document
from app.models.job import Job
from app.models.document_page import DocumentPage
from app.models.tax_session import TaxSession
from app.ocr.providers.base import OCRResult, OCRPage
from app.services.ingestion.pipeline import process_upload


async def _create_session_doc_job(db_session, data: bytes, mime_type: str = "text/plain"):
    session = TaxSession(title="Pipeline Separation", financial_year="2025-2026")
    db_session.add(session)
    await db_session.flush()
    doc = Document(
        session_id=session.id,
        original_filename="sample.txt",
        mime_type=mime_type,
        file_size_bytes=len(data),
        status="uploaded",
    )
    db_session.add(doc)
    await db_session.flush()
    job = Job(
        session_id=session.id,
        document_id=doc.id,
        job_type="ingestion",
        status="queued",
    )
    db_session.add(job)
    await db_session.flush()
    return session, doc, job


async def test_ai_provider_invalid_does_not_block_local_extraction(db_session, monkeypatch):
    data = b"PAYG summary text from local extraction"
    _session, doc, job = await _create_session_doc_job(db_session, data)

    async def _fake_extract_text(file_data, mime_type):
        assert file_data == data
        return OCRResult(pages=[OCRPage(page_number=1, text=data.decode(), confidence=1.0)], method="identity")

    async def _fake_classify_document(*args, **kwargs):
        raise ValueError("Unknown AI_PROVIDER: 'invalid'")

    async def _fake_key(*args, **kwargs):
        return b"k" * 32

    monkeypatch.setattr("app.services.ingestion.pipeline._get_session_field_key", _fake_key)
    monkeypatch.setattr("app.services.ingestion.pipeline.extract_text", _fake_extract_text)
    monkeypatch.setattr("app.services.classification.classify_document", _fake_classify_document)

    try:
        await process_upload(
            db=db_session,
            document_id=doc.id,
            job_id=job.id,
            session_id=doc.session_id,
            original_filename=doc.original_filename,
            mime_type=doc.mime_type,
            file_data=data,
        )
    except Exception:
        # classification failure bubbles up; extraction persistence is what this test validates
        pass

    updated_doc = (await db_session.execute(select(Document).where(Document.id == doc.id))).scalar_one()
    pages = (await db_session.execute(select(DocumentPage).where(DocumentPage.document_id == doc.id))).scalars().all()
    assert len(pages) == 1
    assert updated_doc.extraction_status == "extracted"
    assert updated_doc.extraction_text_length == len(data.decode())
    assert updated_doc.classification_status == "failed"
    assert updated_doc.status in {"classification_failed", "needs_review"}


async def test_extracted_text_preserved_when_classification_fails(db_session, monkeypatch):
    data = b"Local OCR text should be preserved"
    _session, doc, job = await _create_session_doc_job(db_session, data)

    async def _fake_extract_text(file_data, mime_type):
        return OCRResult(pages=[OCRPage(page_number=1, text=data.decode(), confidence=1.0)], method="identity")

    async def _failing_classify_document(*args, **kwargs):
        raise RuntimeError("provider outage")

    async def _fake_key(*args, **kwargs):
        return b"k" * 32

    monkeypatch.setattr("app.services.ingestion.pipeline._get_session_field_key", _fake_key)
    monkeypatch.setattr("app.services.ingestion.pipeline.extract_text", _fake_extract_text)
    monkeypatch.setattr("app.services.classification.classify_document", _failing_classify_document)

    try:
        await process_upload(
            db=db_session,
            document_id=doc.id,
            job_id=job.id,
            session_id=doc.session_id,
            original_filename=doc.original_filename,
            mime_type=doc.mime_type,
            file_data=data,
        )
    except Exception:
        pass

    updated_doc = (await db_session.execute(select(Document).where(Document.id == doc.id))).scalar_one()
    assert updated_doc.extraction_status == "extracted"
    assert (updated_doc.extraction_text_length or 0) > 0
    assert updated_doc.extracted_text_hash == hashlib.sha256(data.decode().encode()).hexdigest()
    assert updated_doc.status_reason == "Text extracted, but classification failed. Manual review required."


async def test_no_text_extracted_sets_ocr_specific_message(db_session, monkeypatch):
    data = b"%PDF-empty-scan%"
    _session, doc, job = await _create_session_doc_job(db_session, data, mime_type="application/pdf")

    async def _empty_extract_text(file_data, mime_type):
        return OCRResult(pages=[OCRPage(page_number=1, text="", confidence=0.0)], method="pdfplumber_fallback_tesseract")

    async def _fake_key(*args, **kwargs):
        return b"k" * 32

    monkeypatch.setattr("app.services.ingestion.pipeline._get_session_field_key", _fake_key)
    monkeypatch.setattr("app.services.ingestion.pipeline.extract_text", _empty_extract_text)

    result = await process_upload(
        db=db_session,
        document_id=doc.id,
        job_id=job.id,
        session_id=doc.session_id,
        original_filename=doc.original_filename,
        mime_type=doc.mime_type,
        file_data=data,
    )
    assert result.document.status == "needs_review"
    assert result.document.extraction_status == "no_text"
    assert result.document.status_reason == "OCR returned no text."


async def test_deepseek_classification_receives_text_only(db_session, monkeypatch):
    data = b"Employment income statement text"
    _session, doc, job = await _create_session_doc_job(db_session, data)
    captured = {"extracted_text": None}

    async def _fake_extract_text(file_data, mime_type):
        return OCRResult(pages=[OCRPage(page_number=1, text=data.decode(), confidence=1.0)], method="identity")

    async def _capture_classify_document(*args, **kwargs):
        captured["extracted_text"] = kwargs.get("extracted_text")
        return []

    async def _fake_key(*args, **kwargs):
        return b"k" * 32

    monkeypatch.setattr("app.services.ingestion.pipeline._get_session_field_key", _fake_key)
    monkeypatch.setattr("app.services.ingestion.pipeline.extract_text", _fake_extract_text)
    monkeypatch.setattr("app.services.classification.classify_document", _capture_classify_document)

    await process_upload(
        db=db_session,
        document_id=doc.id,
        job_id=job.id,
        session_id=doc.session_id,
        original_filename=doc.original_filename,
        mime_type=doc.mime_type,
        file_data=data,
    )
    assert isinstance(captured["extracted_text"], str)
    assert captured["extracted_text"] == data.decode()
