"""Job model — tracks long-running async jobs (ingestion, OCR, classification, export).

Lifecycle: queued → running → succeeded/failed/cancelled/retrying
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, Float, Boolean
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
    workspace_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tax_workspaces.id"), nullable=True,
        comment="Workspace scope for worker isolation",
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True,
        comment="Owner user for auth/workspace isolation",
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
    requires_encryption: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="Whether worker needs encryption capability key to process",
    )
    capability_token_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True,
        comment="Hash of short-lived auth token capability reference",
    )
    capability_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    payload: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="JSON job payload for worker execution context",
    )
    lease_owner: Mapped[str | None] = mapped_column(
        String(80), nullable=True,
        comment="Worker instance that currently owns the lease",
    )
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    heartbeat_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
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
