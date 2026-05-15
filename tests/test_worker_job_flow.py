from datetime import datetime, timedelta, timezone
from sqlalchemy import select

from app.models.job import Job
from app.models.tax_session import TaxSession
from app.repositories.job_repo import JobRepository
from app.services.job.worker import claim_next_job, heartbeat_job, execute_job
from app.services.security.key_cache import cache_session_key, clear_session_key


async def _setup_workspace(async_client):
    res = await async_client.post("/api/auth/setup", json={"master_password": "supersecure123"})
    assert res.status_code == 200
    ws = await async_client.get("/api/workspaces")
    assert ws.status_code == 200
    return ws.json()[0]["id"]


async def test_job_claim_and_heartbeat(db_session):
    repo = JobRepository(db_session)
    job = await repo.create(
        session_id=None,
        document_id=None,
        job_type="export",
        workspace_id="w1",
        user_id="u1",
        requires_encryption=True,
    )
    await db_session.commit()

    claimed = await claim_next_job(db_session, worker_id="worker-a", job_types=["export"], lease_seconds=30)
    assert claimed is not None
    assert claimed.id == job.id
    assert claimed.status == "running"
    assert claimed.lease_owner == "worker-a"

    hb = await heartbeat_job(db_session, job.id, "worker-a", lease_seconds=60)
    assert hb is not None
    assert hb.heartbeat_at is not None


async def test_worker_retries_when_capability_missing(db_session):
    repo = JobRepository(db_session)
    job = await repo.create(
        session_id=None,
        document_id=None,
        job_type="ingestion",
        workspace_id="w1",
        user_id="u1",
        requires_encryption=True,
        capability_token_hash="deadbeef",
        capability_expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        payload='{"stage":"ocr_classification"}',
    )
    await db_session.commit()
    claimed = await claim_next_job(db_session, worker_id="worker-a")
    assert claimed is not None
    try:
        await execute_job(db_session, claimed)
        assert False, "expected missing capability"
    except Exception:
        pass
    await db_session.commit()
    row = await db_session.execute(select(Job).where(Job.id == job.id))
    updated = row.scalar_one()
    assert updated.status == "retrying"
    assert updated.error_message == "encryption_key_missing"


async def test_worker_checks_job_with_capability(db_session):
    token = "cap-token"
    token_hash = __import__("hashlib").sha256(token.encode("utf-8")).hexdigest()
    cache_session_key(token, "u1", b"k" * 32, datetime.now(timezone.utc) + timedelta(minutes=10))

    repo = JobRepository(db_session)
    job = await repo.create(
        session_id=None,
        document_id=None,
        job_type="export",
        workspace_id="w1",
        user_id="u1",
        requires_encryption=True,
        capability_token_hash=token_hash,
        capability_expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        payload='{"stage":"review_pack_generation"}',
    )
    await db_session.commit()
    claimed = await claim_next_job(db_session, worker_id="worker-a")
    result = await execute_job(db_session, claimed)
    assert result["status"] == "checked"
    clear_session_key(token)


async def test_job_create_stores_capability_metadata(db_session):
    from app.services.job import create_job

    job = await create_job(
        db=db_session,
        session_id="s1",
        document_id="d1",
        job_type="ingestion",
        workspace_id="w1",
        user_id="u1",
        requires_encryption=True,
        capability_token="cap-token",
        capability_expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        payload={"stage": "ocr_classification"},
    )
    await db_session.commit()
    row = await db_session.execute(select(Job).where(Job.id == job["id"]))
    saved = row.scalar_one()
    assert saved.workspace_id == "w1"
    assert saved.requires_encryption is True
    assert saved.capability_token_hash is not None
