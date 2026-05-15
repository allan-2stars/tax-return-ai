"""Job model — tracks long-running async jobs (ingestion, OCR, classification, export).

Lifecycle: queued → running → succeeded/failed/cancelled/retrying
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tax_sessions.id"), nullable=True,
        comment="Session this job belongs to (nullable for system jobs)",
    )
    document_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("documents.id"), nullable=True,
        comment="Document this job processes (nullable for session-level jobs)",
    )
    job_type: Mapped[str] = mapped_column(
        String(30), nullable=False,
        comment="ingestion / ocr / classification / export / compliance_review",
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="queued",
        comment="queued / running / succeeded / failed / cancelled / retrying",
    )
    progress: Mapped[float | None] = mapped_column(
        Float, nullable=True, default=None,
        comment="Progress 0.0–1.0 for UI progress bars",
    )
    progress_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, default=None,
        comment="Human-readable progress detail",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, default=None,
        comment="Error details if failed",
    )
    result_summary: Mapped[str | None] = mapped_column(
        Text, nullable=True, default=None,
        comment="JSON summary of job result (non-sensitive metadata)",
    )
    queued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<Job id={self.id} type={self.job_type} "
            f"status={self.status} doc={self.document_id}>"
        )
