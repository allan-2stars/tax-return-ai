"""Worker-aware job execution primitives.

Design notes:
- Durable job lifecycle is DB-backed (queued/running/succeeded/failed/retrying)
- Lease/heartbeat model enables future multi-worker deployment
- Encryption capability is token-hash scoped and time-limited
- No master/encryption key material is persisted to disk
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.models.unlock_capability import UnlockCapability
from app.repositories.job_repo import JobRepository
from app.services.audit.writer import write_audit
from app.services.security.key_cache import get_session_key_by_hash
from app.services.security.field_encryption import EncryptionKeyUnavailableError


async def claim_next_job(
    db: AsyncSession,
    worker_id: str,
    job_types: list[str] | None = None,
    lease_seconds: int = 120,
) -> Job | None:
    repo = JobRepository(db)
    return await repo.claim_next(worker_id=worker_id, job_types=job_types, lease_seconds=lease_seconds)


async def heartbeat_job(db: AsyncSession, job_id: str, worker_id: str, lease_seconds: int = 120) -> Job | None:
    repo = JobRepository(db)
    return await repo.heartbeat(job_id=job_id, worker_id=worker_id, lease_seconds=lease_seconds)


async def execute_job(db: AsyncSession, job: Job) -> dict[str, Any]:
    """Execute one claimed job.

    Current phase provides worker-aware lifecycle and encryption capability checks.
    Heavy processing handlers stay in current services and are invoked by API/background flow.
    """
    payload = {}
    if job.payload:
        try:
            payload = json.loads(job.payload)
        except Exception:
            payload = {}

    if job.requires_encryption:
        key = await _resolve_job_key(db, job)
        if not key:
            await _mark_retryable_key_block(db, job)
            raise EncryptionKeyUnavailableError("Encryption capability missing for job")

    await write_audit(
        db,
        "job",
        job.id,
        "worker_job_checked",
        details={"job_type": job.job_type, "attempt_count": job.attempt_count},
    )
    await db.flush()
    return {"job_id": job.id, "status": "checked", "job_type": job.job_type}


async def _resolve_job_key(db: AsyncSession, job: Job) -> bytes | None:
    if not job.capability_token_hash:
        return None
    cap_row = await db.execute(
        select(UnlockCapability).where(UnlockCapability.session_token_hash == job.capability_token_hash)
    )
    capability = cap_row.scalar_one_or_none()
    if not capability or capability.revoked_at is not None:
        return None
    if job.capability_expires_at:
        now = datetime.now(timezone.utc)
        exp = job.capability_expires_at if job.capability_expires_at.tzinfo else job.capability_expires_at.replace(tzinfo=timezone.utc)
        if exp <= now:
            return None
    now = datetime.now(timezone.utc)
    cap_exp = capability.expires_at if capability.expires_at.tzinfo else capability.expires_at.replace(tzinfo=timezone.utc)
    if cap_exp <= now:
        return None
    return get_session_key_by_hash(job.capability_token_hash)


async def _mark_retryable_key_block(db: AsyncSession, job: Job) -> None:
    job.status = "retrying"
    job.progress_message = "Waiting for unlocked encryption capability"
    job.error_message = "encryption_key_missing"
    job.lease_owner = None
    job.lease_expires_at = None
    await write_audit(
        db,
        "job",
        job.id,
        "encryption_key_missing",
        details={"job_type": job.job_type},
    )
    await db.flush()
