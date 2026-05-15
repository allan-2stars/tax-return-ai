"""Tests for the document ingestion pipeline.

Covers:
  - process_upload: end-to-end upload flow (pre-created doc + job)
  - _check_hash_duplicate: SHA-256 deduplication
  - UploadResult shape
"""
import pytest
import hashlib
from sqlalchemy import select
from app.services.ingestion.pipeline import process_upload, _check_hash_duplicate
from app.services.ingestion.deduplication import compute_file_hash
from app.models.document import Document
from app.models.job import Job


class TestIngestionPipeline:
    """Integration tests requiring a DB session."""

    async def _create_session(self, db):
        """Helper to create a minimal session for document binding."""
        from app.models.tax_session import TaxSession
        s = TaxSession(title="Ingestion Test Session", financial_year="2025-2026")
        db.add(s)
        await db.flush()
        return s.id

    async def _create_document(self, db, session_id, filename="test.txt",
                                mime_type="text/plain", data=b"test"):
        """Helper to pre-create a document record (as the upload endpoint does)."""
        doc = Document(
            session_id=session_id,
            original_filename=filename,
            mime_type=mime_type,
            file_size_bytes=len(data),
            status="uploaded",
        )
        db.add(doc)
        await db.flush()
        return doc.id

    async def _create_job(self, db, document_id, session_id):
        """Helper to pre-create a job record."""
        job = Job(
            session_id=session_id,
            document_id=document_id,
            job_type="ingestion",
            status="queued",
        )
        db.add(job)
        await db.flush()
        return job.id

    async def test_process_upload_updates_document(self, db_session):
        """Uploading a file should update the pre-created Document record."""
        sid = await self._create_session(db_session)
        data = b"test file content for ingestion"
        doc_id = await self._create_document(db_session, sid, data=data)
        job_id = await self._create_job(db_session, doc_id, sid)

        result = await process_upload(
            db=db_session,
            document_id=doc_id,
            job_id=job_id,
            session_id=sid,
            original_filename="receipt.txt",
            mime_type="text/plain",
            file_data=data,
        )

        assert result.document is not None
        assert result.document.id == doc_id
        assert result.document.original_filename == "receipt.txt"
        assert result.document.mime_type == "text/plain"
        assert result.document.file_size_bytes == len(data)
        assert result.document.session_id == sid
        assert result.duplicate_of is None

        # Verify job was completed
        stmt = select(Job).where(Job.id == job_id)
        job = (await db_session.execute(stmt)).scalar_one()
        assert job.status == "succeeded"

    async def test_process_upload_computes_hash(self, db_session):
        """Upload should compute and store SHA-256 hash."""
        sid = await self._create_session(db_session)
        data = b"unique content for hash test"
        doc_id = await self._create_document(db_session, sid, data=data)
        job_id = await self._create_job(db_session, doc_id, sid)

        result = await process_upload(
            db=db_session, document_id=doc_id, job_id=job_id,
            session_id=sid,
            original_filename="hash_test.txt",
            mime_type="text/plain", file_data=data,
        )

        expected_hash = hashlib.sha256(data).hexdigest()
        assert result.document.file_hash == expected_hash
        assert len(result.document.file_hash) == 64

    async def test_process_upload_detects_duplicate_by_hash(self, db_session):
        """Same file hash in same session should be flagged as duplicate."""
        sid = await self._create_session(db_session)
        data = b"duplicate test content"
        doc1_id = await self._create_document(db_session, sid, "original.txt", data=data)
        job1_id = await self._create_job(db_session, doc1_id, sid)

        # First upload
        first = await process_upload(
            db=db_session, document_id=doc1_id, job_id=job1_id,
            session_id=sid,
            original_filename="original.txt",
            mime_type="text/plain", file_data=data,
        )

        # Second upload — same content, different name
        doc2_id = await self._create_document(db_session, sid, "renamed_copy.txt", data=data)
        job2_id = await self._create_job(db_session, doc2_id, sid)

        second = await process_upload(
            db=db_session, document_id=doc2_id, job_id=job2_id,
            session_id=sid,
            original_filename="renamed_copy.txt",
            mime_type="text/plain", file_data=data,
        )

        assert second.duplicate_of == first.document.id
        assert second.document.status == "duplicate_detected"
        assert first.document.id in (second.document.status_reason or "")

    async def test_different_sessions_allow_same_hash(self, db_session):
        """Same file uploaded to different sessions should NOT be duplicate."""
        sid1 = await self._create_session(db_session)
        sid2 = await self._create_session(db_session)
        data = b"shared content"
        doc1_id = await self._create_document(db_session, sid1, "doc1.txt", data=data)
        job1_id = await self._create_job(db_session, doc1_id, sid1)
        doc2_id = await self._create_document(db_session, sid2, "doc2.txt", data=data)
        job2_id = await self._create_job(db_session, doc2_id, sid2)

        await process_upload(
            db=db_session, document_id=doc1_id, job_id=job1_id,
            session_id=sid1,
            original_filename="doc1.txt",
            mime_type="text/plain", file_data=data,
        )

        result = await process_upload(
            db=db_session, document_id=doc2_id, job_id=job2_id,
            session_id=sid2,
            original_filename="doc2.txt",
            mime_type="text/plain", file_data=data,
        )

        assert result.duplicate_of is None
        assert result.document.status != "duplicate_detected"

    async def test_non_duplicate_pipeline_status(self, db_session):
        """Non-duplicate uploads should progress through pipeline statuses."""
        sid = await self._create_session(db_session)
        data = b"fresh document"
        doc_id = await self._create_document(db_session, sid, "fresh.txt", data=data)
        job_id = await self._create_job(db_session, doc_id, sid)

        result = await process_upload(
            db=db_session, document_id=doc_id, job_id=job_id,
            session_id=sid,
            original_filename="fresh.txt",
            mime_type="text/plain", file_data=data,
        )

        assert result.document.status == "classified"
        # Verify the document is in DB
        stmt = select(Document).where(Document.id == result.document.id)
        doc = (await db_session.execute(stmt)).scalar_one()
        assert doc.status == "classified"

        # Verify a TaxItem was created
        from app.models.tax_item import TaxItem
        item_stmt = select(TaxItem).where(TaxItem.session_id == sid)
        items = (await db_session.execute(item_stmt)).scalars().all()
        assert len(items) >= 1

    async def test_empty_file_upload(self, db_session):
        """Empty files should still be accepted (handled by router-level check)."""
        sid = await self._create_session(db_session)
        data = b""
        doc_id = await self._create_document(db_session, sid, "empty.txt", data=data)
        job_id = await self._create_job(db_session, doc_id, sid)

        result = await process_upload(
            db=db_session, document_id=doc_id, job_id=job_id,
            session_id=sid,
            original_filename="empty.txt",
            mime_type="text/plain", file_data=data,
        )
        assert result.document.file_size_bytes == 0
        assert result.document.file_hash == hashlib.sha256(b"").hexdigest()

    async def test_text_upload_creates_document_pages(self, db_session):
        """Text file upload should create DocumentPage records via identity OCR."""
        from app.models.document_page import DocumentPage

        sid = await self._create_session(db_session)
        data = b"Payment summary: ABC Corp, Salary, $85,000"
        doc_id = await self._create_document(db_session, sid, "summary.txt", data=data)
        job_id = await self._create_job(db_session, doc_id, sid)

        result = await process_upload(
            db=db_session, document_id=doc_id, job_id=job_id,
            session_id=sid,
            original_filename="summary.txt",
            mime_type="text/plain", file_data=data,
        )

        # Verify document pages were created
        stmt = select(DocumentPage).where(
            DocumentPage.document_id == result.document.id
        )
        pages = (await db_session.execute(stmt)).scalars().all()
        assert len(pages) == 1
        assert pages[0].page_number == 1
        assert "ABC Corp" in (pages[0].text or "")
        assert pages[0].confidence == 1.0

    async def test_upload_sets_audit_event(self, db_session):
        """Upload should write an audit log entry."""
        from app.models.audit_log import AuditLog

        sid = await self._create_session(db_session)
        data = b"auditable upload"
        doc_id = await self._create_document(db_session, sid, "audit_test.txt", data=data)
        job_id = await self._create_job(db_session, doc_id, sid)

        result = await process_upload(
            db=db_session, document_id=doc_id, job_id=job_id,
            session_id=sid,
            original_filename="audit_test.txt",
            mime_type="text/plain", file_data=data,
        )

        stmt = select(AuditLog).where(
            AuditLog.entity_id == result.document.id,
            AuditLog.action == "uploaded",
        )
        entry = (await db_session.execute(stmt)).scalar_one_or_none()
        assert entry is not None
        assert entry.entity_type == "document"
        assert "filename" in (entry.details or {})


class TestDeduplication:
    """Unit tests for the deduplication helper."""

    def test_compute_file_hash_returns_sha256(self):
        h = compute_file_hash(b"test")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_same_bytes_same_hash(self):
        assert compute_file_hash(b"hello") == compute_file_hash(b"hello")

    def test_different_bytes_different_hash(self):
        assert compute_file_hash(b"hello") != compute_file_hash(b"world")
