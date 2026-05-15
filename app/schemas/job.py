"""Job Pydantic schemas."""
from datetime import datetime
from pydantic import BaseModel


class JobCreate(BaseModel):
    session_id: str | None = None
    document_id: str | None = None
    job_type: str


class JobUpdate(BaseModel):
    status: str | None = None
    progress: float | None = None
    progress_message: str | None = None
    error_message: str | None = None
    result_summary: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class JobStatusResponse(BaseModel):
    id: str
    session_id: str | None
    document_id: str | None
    job_type: str
    status: str
    progress: float | None
    progress_message: str | None
    error_message: str | None
    result_summary: str | None
    queued_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobResponse(BaseModel):
    id: str
    session_id: str | None
    document_id: str | None
    job_type: str
    status: str
    progress: float | None
    progress_message: str | None
    error_message: str | None
    result_summary: str | None
    queued_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
