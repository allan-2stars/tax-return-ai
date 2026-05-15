"""Job repository — all DB queries for jobs."""
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, update, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.job import Job


class JobRepository:
    """Repository for Job CRUD operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        session_id: str | None,
        document_id: str | None,
        job_type: str,
        workspace_id: str | None = None,
        user_id: str | None = None,
        requires_encryption: bool = False,
        capability_token_hash: str | None = None,
        capability_expires_at: datetime | None = None,
        payload: str | None = None,
    ) -> Job:
        """Create a new job in queued status."""
        job = Job(
            session_id=session_id,
            document_id=document_id,
            job_type=job_type,
            status="queued",
            workspace_id=workspace_id,
            user_id=user_id,
            requires_encryption=requires_encryption,
            capability_token_hash=capability_token_hash,
            capability_expires_at=capability_expires_at,
            payload=payload,
        )
        self.db.add(job)
        await self.db.flush()
        return job

    async def get(self, job_id: str) -> Job | None:
        """Get a job by ID."""
        result = await self.db.execute(select(Job).where(Job.id == job_id))
        return result.scalar_one_or_none()

    async def find_by_session(self, session_id: str) -> list[Job]:
        """Find all jobs for a session, newest first."""
        result = await self.db.execute(
            select(Job)
            .where(Job.session_id == session_id)
            .order_by(Job.created_at.desc())
        )
        return list(result.scalars().all())

    async def find_by_document(self, document_id: str) -> list[Job]:
        """Find all jobs for a document, newest first."""
        result = await self.db.execute(
            select(Job)
            .where(Job.document_id == document_id)
            .order_by(Job.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_status(self, job_id: str, status: str,
                            **extra_fields) -> Job | None:
        """Update job status and optional extra fields.

        Automatically sets started_at/completed_at based on status transitions.
        """
        updates = {"status": status}
        if status == "running":
            from datetime import datetime, timezone
            updates["started_at"] = datetime.now(timezone.utc)
        elif status in ("succeeded", "failed", "cancelled"):
            from datetime import datetime, timezone
            updates["completed_at"] = datetime.now(timezone.utc)

        updates.update(extra_fields)

        stmt = (
            update(Job)
            .where(Job.id == job_id)
            .values(**updates)
        )
        await self.db.execute(stmt)
        await self.db.flush()
        return await self.get(job_id)

    async def claim_next(
        self,
        worker_id: str,
        job_types: list[str] | None = None,
        lease_seconds: int = 120,
    ) -> Job | None:
        now = datetime.now(timezone.utc)
        stmt = select(Job).where(
            Job.status.in_(["queued", "retrying"]),
            or_(Job.lease_expires_at.is_(None), Job.lease_expires_at <= now),
        ).order_by(Job.created_at.asc())
        if job_types:
            stmt = stmt.where(Job.job_type.in_(job_types))
        result = await self.db.execute(stmt.limit(1))
        job = result.scalar_one_or_none()
        if not job:
            return None
        job.lease_owner = worker_id
        job.lease_expires_at = now + timedelta(seconds=lease_seconds)
        job.heartbeat_at = now
        job.attempt_count = (job.attempt_count or 0) + 1
        job.status = "running"
        job.started_at = now
        await self.db.flush()
        return job

    async def heartbeat(self, job_id: str, worker_id: str, lease_seconds: int = 120) -> Job | None:
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(Job).where(
                Job.id == job_id,
                Job.lease_owner == worker_id,
                Job.status == "running",
            )
        )
        job = result.scalar_one_or_none()
        if not job:
            return None
        job.heartbeat_at = now
        job.lease_expires_at = now + timedelta(seconds=lease_seconds)
        await self.db.flush()
        return job
