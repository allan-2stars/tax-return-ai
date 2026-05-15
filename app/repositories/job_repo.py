"""Job repository — all DB queries for jobs."""
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.job import Job


class JobRepository:
    """Repository for Job CRUD operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, session_id: str | None, document_id: str | None,
                     job_type: str) -> Job:
        """Create a new job in queued status."""
        job = Job(
            session_id=session_id,
            document_id=document_id,
            job_type=job_type,
            status="queued",
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
