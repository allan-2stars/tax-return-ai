"""Classification result model — raw validated AI JSON per classification run."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class ClassificationResultModel(Base):
    __tablename__ = "classification_results"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id"), nullable=False
    )
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tax_sessions.id"), nullable=False
    )
    provider_name: Mapped[str] = mapped_column(
        String(30), nullable=False
    )
    raw_input: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    raw_output: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    parsed_output: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Validated JSON output"
    )
    confidence: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    processing_time_ms: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    success: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    model_version: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<ClassificationResultModel id={self.id} "
            f"document_id={self.document_id} "
            f"provider={self.provider_name} "
            f"success={self.success}>"
        )
