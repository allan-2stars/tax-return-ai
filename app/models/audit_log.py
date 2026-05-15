"""AuditLog model — append-only event log."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    entity_type: Mapped[str] = mapped_column(
        String(30), nullable=False,
        comment="e.g. tax_session, document, tax_item"
    )
    entity_id: Mapped[str] = mapped_column(
        String(36), nullable=False
    )
    action: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="created / updated / deleted / reviewed / exported"
    )
    changed_by: Mapped[str | None] = mapped_column(
        String(50), nullable=True, default="system"
    )
    details: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="JSON or human-readable change details"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog {self.entity_type}({self.entity_id}) "
            f"action={self.action}>"
        )
