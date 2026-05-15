"""Job management routes — create, poll, list jobs.

Endpoints:
- POST /api/jobs — create a new job
- GET /api/jobs/{job_id} — full job details
- GET /api/jobs/{job_id}/status — lightweight status poll
- GET /api/jobs — list jobs (filter by session_id or document_id)
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.deps import get_db
from app.schemas.job import JobCreate, JobStatusResponse, JobResponse
from app.services.job import (
    create_job,
    get_job,
    get_job_status,
    list_jobs_for_session,
    list_jobs_for_document,
)

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job_endpoint(
    data: JobCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new queued job."""
    job = await create_job(
        db=db,
        session_id=data.session_id,
        document_id=data.document_id,
        job_type=data.job_type,
    )
    await db.commit()
    return job


@router.get("", response_model=list[JobResponse])
async def list_jobs(
    session_id: str | None = Query(default=None),
    document_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """List jobs, filtered by session_id or document_id."""
    if session_id:
        return await list_jobs_for_session(db, session_id)
    elif document_id:
        return await list_jobs_for_document(db, document_id)
    raise HTTPException(
        status_code=400,
        detail="Must provide session_id or document_id filter",
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job_endpoint(
    job_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get full job details."""
    job = await get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status_endpoint(
    job_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Lightweight status poll — returns status, progress, error."""
    job = await get_job_status(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
