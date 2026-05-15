"""Monitoring routes — expose internal state for debugging."""
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.deps import get_db
from app.models.job import Job

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


@router.get("/jobs/summary")
async def job_summary(db: AsyncSession = Depends(get_db)):
    """Return counts of jobs by status — quick health check for background tasks."""
    result = await db.execute(
        select(Job.status, func.count(Job.id))
        .group_by(Job.status)
    )
    counts = {row[0]: row[1] for row in result.all()}
    return {
        "total": sum(counts.values()),
        "by_status": counts,
    }
