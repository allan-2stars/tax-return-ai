"""Job service — orchestrates job lifecycle.

Provides:
- create_job: Create a new queued job and return it
- update_job_status: Update job status with timestamps
- run_job_sync: Execute a job function and update status
  (synchronous in-process — future: background worker)
"""
import json
import traceback
import hashlib
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.job_repo import JobRepository
from app.services.audit.writer import write_audit


async def create_job(
    db: AsyncSession,
    session_id: str | None,
    document_id: str | None,
    job_type: str,
    workspace_id: str | None = None,
    user_id: str | None = None,
    requires_encryption: bool = False,
    capability_token: str | None = None,
    capability_expires_at: datetime | None = None,
    payload: dict | None = None,
) -> dict:
    """Create a new job in queued status.

    Returns the job as a dict for use in API responses.
    """
    repo = JobRepository(db)
    capability_token_hash = (
        hashlib.sha256(capability_token.encode("utf-8")).hexdigest()
        if capability_token
        else None
    )
    job = await repo.create(
        session_id=session_id,
        document_id=document_id,
        job_type=job_type,
        workspace_id=workspace_id,
        user_id=user_id,
        requires_encryption=requires_encryption,
        capability_token_hash=capability_token_hash,
        capability_expires_at=capability_expires_at,
        payload=json.dumps(payload, separators=(",", ":")) if payload is not None else None,
    )
    await write_audit(
        db, "job", job.id, "created",
        details={
            "job_type": job_type,
            "session_id": session_id,
            "document_id": document_id,
            "workspace_id": workspace_id,
            "requires_encryption": requires_encryption,
        },
    )
    return _job_to_dict(job)


async def get_job(db: AsyncSession, job_id: str) -> dict | None:
    """Get a single job."""
    repo = JobRepository(db)
    job = await repo.get(job_id)
    return _job_to_dict(job) if job else None


async def get_job_status(db: AsyncSession, job_id: str) -> dict | None:
    """Get job status summary (lightweight, no session/doc expansion)."""
    repo = JobRepository(db)
    job = await repo.get(job_id)
    if not job:
        return None
    return {
        "id": job.id,
        "session_id": job.session_id,
        "document_id": job.document_id,
        "status": job.status,
        "job_type": job.job_type,
        "progress": job.progress,
        "progress_message": job.progress_message,
        "error_message": job.error_message,
        "result_summary": job.result_summary,
        "queued_at": job.queued_at.isoformat() if job.queued_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }


async def list_jobs_for_session(db: AsyncSession, session_id: str) -> list[dict]:
    """List all jobs for a session."""
    repo = JobRepository(db)
    jobs = await repo.find_by_session(session_id)
    return [_job_to_dict(j) for j in jobs]


async def list_jobs_for_document(db: AsyncSession, document_id: str) -> list[dict]:
    """List all jobs for a document."""
    repo = JobRepository(db)
    jobs = await repo.find_by_document(document_id)
    return [_job_to_dict(j) for j in jobs]


async def update_job_status(
    db: AsyncSession,
    job_id: str,
    status: str,
    progress: float | None = None,
    progress_message: str | None = None,
    error_message: str | None = None,
    result_summary: str | None = None,
) -> dict | None:
    """Update job status with automatic timestamp management."""
    repo = JobRepository(db)
    updates = {}
    if progress is not None:
        updates["progress"] = progress
    if progress_message is not None:
        updates["progress_message"] = progress_message
    if error_message is not None:
        updates["error_message"] = error_message
    if result_summary is not None:
        updates["result_summary"] = result_summary

    job = await repo.update_status(job_id, status, **updates)
    if job:
        await write_audit(
            db, "job", job_id, f"status_{status}",
            details={"status": status, "progress": progress},
        )
    return _job_to_dict(job) if job else None


async def run_job_sync(
    db: AsyncSession,
    job_id: str,
    job_fn,
    progress_callback=None,
) -> dict:
    """Execute a job function synchronously with status tracking.

    Wraps a coroutine with queued → running → succeeded/failed lifecycle.

    Args:
        db: Database session
        job_id: Job ID to update
        job_fn: Async callable that does the actual work
        progress_callback: Optional async fn(job_id, progress, message)

    Returns:
        Updated job as dict
    """
    # Mark as running
    now = datetime.now(timezone.utc)
    await update_job_status(db, job_id, "running", progress=0.0,
                            progress_message="Starting...")

    try:
        result = await job_fn()
        summary = json.dumps(result, default=str) if isinstance(result, dict) else str(result)
        return await update_job_status(
            db, job_id, "succeeded",
            progress=1.0,
            progress_message="Completed",
            result_summary=summary,
        )
    except Exception as exc:
        tb = traceback.format_exc()
        return await update_job_status(
            db, job_id, "failed",
            progress=None,
            error_message=f"{type(exc).__name__}: {exc}\n{tb[:500]}",
        )


def _job_to_dict(job) -> dict | None:
    """Convert Job ORM model to a plain dict for API responses."""
    if job is None:
        return None
    return {
        "id": job.id,
        "session_id": job.session_id,
        "workspace_id": job.workspace_id,
        "user_id": job.user_id,
        "document_id": job.document_id,
        "job_type": job.job_type,
        "status": job.status,
        "requires_encryption": job.requires_encryption,
        "progress": job.progress,
        "progress_message": job.progress_message,
        "error_message": job.error_message,
        "result_summary": job.result_summary,
        "queued_at": job.queued_at.isoformat() if job.queued_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }
