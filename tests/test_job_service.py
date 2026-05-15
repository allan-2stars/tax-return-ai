"""Tests for the Job system — model, repository, service, and endpoints.

Covers:
  - Job model: creation, defaults, field types
  - JobRepository: create, get, find, update_status
  - Job service: create_job, update_job_status, run_job_sync
  - Job endpoints: create, list, get, status poll
"""
import pytest
from datetime import datetime, timezone
from sqlalchemy import select
from app.models.job import Job
from app.repositories.job_repo import JobRepository
from app.services.job import (
    create_job,
    update_job_status,
    run_job_sync,
    get_job,
    get_job_status,
    list_jobs_for_session,
    list_jobs_for_document,
)


# ── Model Tests ─────────────────────────────────────────────────────────────


class TestJobModel:
    """Tests for the Job ORM model."""

    async def test_create_job_minimal(self, db_session):
        job = Job(job_type="ingestion")
        db_session.add(job)
        await db_session.flush()

        assert job.id is not None
        assert len(job.id) == 36  # UUID
        assert job.status == "queued"
        assert job.job_type == "ingestion"
        assert job.session_id is None
        assert job.document_id is None
        assert job.progress is None
        assert job.error_message is None
        assert job.queued_at is not None
        assert job.created_at is not None
        assert job.updated_at is not None

    async def test_create_job_full(self, db_session):
        """Create a job with all optional fields."""
        from app.models.tax_session import TaxSession
        from app.models.document import Document

        session = TaxSession(title="Job Test", financial_year="2025-2026")
        db_session.add(session)
        await db_session.flush()

        doc = Document(
            session_id=session.id,
            original_filename="test.pdf",
            mime_type="application/pdf",
            file_size_bytes=1024,
            status="uploaded",
        )
        db_session.add(doc)
        await db_session.flush()

        job = Job(
            session_id=session.id,
            document_id=doc.id,
            job_type="ocr",
            status="queued",
        )
        db_session.add(job)
        await db_session.flush()

        assert job.session_id == session.id
        assert job.document_id == doc.id
        assert job.job_type == "ocr"

    async def test_job_str_repr(self, db_session):
        job = Job(job_type="classification", status="running")
        db_session.add(job)
        await db_session.flush()

        text = repr(job)
        assert job.id in text
        assert "classification" in text
        assert "running" in text


# ── Repository Tests ─────────────────────────────────────────────────────────


class TestJobRepository:
    """Tests for JobRepository."""

    async def _create_session(self, db):
        from app.models.tax_session import TaxSession
        s = TaxSession(title="Repo Test", financial_year="2025-2026")
        db.add(s)
        await db.flush()
        return s.id

    @pytest.fixture
    def repo(self, db_session):
        return JobRepository(db_session)

    async def test_create_job(self, repo, db_session):
        sid = await self._create_session(db_session)
        job = await repo.create(session_id=sid, document_id=None, job_type="ingestion")

        assert job.id is not None
        assert job.job_type == "ingestion"
        assert job.status == "queued"
        assert job.session_id == sid

    async def test_get_job(self, repo, db_session):
        job = await repo.create(session_id=None, document_id=None, job_type="export")

        fetched = await repo.get(job.id)
        assert fetched is not None
        assert fetched.id == job.id
        assert fetched.job_type == "export"

    async def test_get_job_not_found(self, repo):
        assert await repo.get("nonexistent-id") is None

    async def test_find_by_session(self, repo, db_session):
        sid = await self._create_session(db_session)
        job1 = await repo.create(session_id=sid, document_id=None, job_type="ingestion")
        job2 = await repo.create(session_id=sid, document_id=None, job_type="classification")

        jobs = await repo.find_by_session(sid)
        assert len(jobs) == 2
        # Newest first
        assert jobs[0].id == job2.id

    async def test_find_by_document(self, repo, db_session):
        sid = await self._create_session(db_session)
        from app.models.document import Document
        doc = Document(
            session_id=sid, original_filename="doc.pdf",
            mime_type="application/pdf", file_size_bytes=512, status="uploaded",
        )
        db_session.add(doc)
        await db_session.flush()

        job = await repo.create(session_id=sid, document_id=doc.id, job_type="ocr")
        jobs = await repo.find_by_document(doc.id)
        assert len(jobs) == 1
        assert jobs[0].id == job.id

    async def test_update_status_to_running(self, repo, db_session):
        job = await repo.create(session_id=None, document_id=None, job_type="ingestion")
        assert job.status == "queued"

        updated = await repo.update_status(job.id, "running")
        assert updated is not None
        assert updated.status == "running"
        assert updated.started_at is not None

    async def test_update_status_to_succeeded(self, repo, db_session):
        job = await repo.create(session_id=None, document_id=None, job_type="ingestion")
        await repo.update_status(job.id, "running")

        updated = await repo.update_status(
            job.id, "succeeded",
            progress=1.0, progress_message="Done",
            result_summary='{"status": "ok"}',
        )
        assert updated.status == "succeeded"
        assert updated.progress == 1.0
        assert updated.progress_message == "Done"
        assert updated.completed_at is not None

    async def test_update_status_to_failed(self, repo, db_session):
        job = await repo.create(session_id=None, document_id=None, job_type="ingestion")
        await repo.update_status(job.id, "running")

        updated = await repo.update_status(
            job.id, "failed",
            error_message="Something went wrong",
        )
        assert updated.status == "failed"
        assert updated.error_message == "Something went wrong"
        assert updated.completed_at is not None


# ── Service Tests ────────────────────────────────────────────────────────────


class TestJobService:
    """Tests for the job service layer."""

    async def _create_session(self, db):
        from app.models.tax_session import TaxSession
        s = TaxSession(title="Service Test", financial_year="2025-2026")
        db.add(s)
        await db.flush()
        return s.id

    async def test_create_job_service(self, db_session):
        sid = await self._create_session(db_session)
        result = await create_job(
            db=db_session, session_id=sid, document_id=None, job_type="ingestion",
        )
        assert result["id"] is not None
        assert result["job_type"] == "ingestion"
        assert result["status"] == "queued"
        assert result["session_id"] == sid

    async def test_get_job_service(self, db_session):
        sid = await self._create_session(db_session)
        created = await create_job(db_session, sid, None, "export")

        fetched = await get_job(db_session, created["id"])
        assert fetched is not None
        assert fetched["id"] == created["id"]

    async def test_get_job_status_lightweight(self, db_session):
        sid = await self._create_session(db_session)
        created = await create_job(db_session, sid, None, "ocr")

        status = await get_job_status(db_session, created["id"])
        assert status is not None
        assert status["id"] == created["id"]
        assert status["status"] == "queued"
        assert "queued_at" in status
        # Lightweight: no full response fields
        assert "session_id" not in status

    async def test_update_job_status_service(self, db_session):
        sid = await self._create_session(db_session)
        created = await create_job(db_session, sid, None, "ingestion")

        updated = await update_job_status(
            db_session, created["id"], "running", progress=0.5,
        )
        assert updated["status"] == "running"
        assert updated["progress"] == 0.5
        assert updated["started_at"] is not None

    async def test_run_job_sync_success(self, db_session):
        sid = await self._create_session(db_session)
        created = await create_job(db_session, sid, None, "classification")

        async def fake_task():
            return {"items": 5, "status": "ok"}

        result = await run_job_sync(db_session, created["id"], fake_task)
        assert result["status"] == "succeeded"
        assert result["progress"] == 1.0

    async def test_run_job_sync_failure(self, db_session):
        sid = await self._create_session(db_session)
        created = await create_job(db_session, sid, None, "ingestion")

        async def failing_task():
            raise ValueError("OCR failed")

        result = await run_job_sync(db_session, created["id"], failing_task)
        assert result["status"] == "failed"
        assert "ValueError: OCR failed" in (result["error_message"] or "")

    async def test_list_jobs_for_session(self, db_session):
        sid = await self._create_session(db_session)
        await create_job(db_session, sid, None, "ingestion")
        await create_job(db_session, sid, None, "classification")

        jobs = await list_jobs_for_session(db_session, sid)
        assert len(jobs) == 2

    async def test_list_jobs_for_document(self, db_session):
        sid = await self._create_session(db_session)
        from app.models.document import Document
        doc = Document(
            session_id=sid, original_filename="doc.pdf",
            mime_type="application/pdf", file_size_bytes=512, status="uploaded",
        )
        db_session.add(doc)
        await db_session.flush()

        await create_job(db_session, sid, doc.id, "ocr")
        await create_job(db_session, sid, doc.id, "classification")

        jobs = await list_jobs_for_document(db_session, doc.id)
        assert len(jobs) == 2


# ── Endpoint Tests ──────────────────────────────────────────────────────────


class TestJobEndpoints:
    """Tests for the /api/jobs endpoints."""

    async def _create_session(self, client):
        resp = await client.post("/api/sessions", json={
            "title": "Job EP Test", "financial_year": "2025-2026",
        })
        return resp.json()["id"]

    async def test_create_job_endpoint(self, async_client):
        sid = await self._create_session(async_client)
        resp = await async_client.post("/api/jobs", json={
            "session_id": sid,
            "document_id": None,
            "job_type": "ingestion",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] is not None
        assert data["job_type"] == "ingestion"
        assert data["status"] == "queued"

    async def test_get_job_endpoint(self, async_client):
        sid = await self._create_session(async_client)
        create_resp = await async_client.post("/api/jobs", json={
            "session_id": sid, "document_id": None, "job_type": "export",
        })
        job_id = create_resp.json()["id"]

        resp = await async_client.get(f"/api/jobs/{job_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == job_id

    async def test_get_job_status_endpoint(self, async_client):
        sid = await self._create_session(async_client)
        create_resp = await async_client.post("/api/jobs", json={
            "session_id": sid, "document_id": None, "job_type": "ingestion",
        })
        job_id = create_resp.json()["id"]

        resp = await async_client.get(f"/api/jobs/{job_id}/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == job_id
        assert data["status"] == "queued"
        assert "queued_at" in data
        # Lightweight — no full response
        assert "session_id" not in data

    async def test_get_job_404(self, async_client):
        resp = await async_client.get("/api/jobs/nonexistent-id")
        assert resp.status_code == 404

    async def test_list_jobs_by_session(self, async_client):
        sid = await self._create_session(async_client)
        await async_client.post("/api/jobs", json={
            "session_id": sid, "document_id": None, "job_type": "ingestion",
        })
        await async_client.post("/api/jobs", json={
            "session_id": sid, "document_id": None, "job_type": "classification",
        })

        resp = await async_client.get(f"/api/jobs?session_id={sid}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    async def test_list_jobs_missing_filter_returns_400(self, async_client):
        resp = await async_client.get("/api/jobs")
        assert resp.status_code == 400
        assert "filter" in resp.text.lower()
