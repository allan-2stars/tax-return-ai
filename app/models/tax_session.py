"""TaxSession model — groups documents for one user + one financial year."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.constants.risk import TaxSessionStatus


class TaxSession(Base):
    __tablename__ = "tax_sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    workspace_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tax_workspaces.id"), nullable=True
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    financial_year: Mapped[str] = mapped_column(
        String(9), nullable=False, default="2025-2026"
    )
    status: Mapped[str] = mapped_column(
        SAEnum(TaxSessionStatus, name="tax_session_status", length=20),
        nullable=False,
        default=TaxSessionStatus.draft.value,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
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

    # Relationships
    documents = relationship("Document", back_populates="session", lazy="selectin")
    tax_items = relationship("TaxItem", back_populates="session", lazy="selectin")

    def __repr__(self) -> str:
        return f"<TaxSession id={self.id} fy={self.financial_year} status={self.status}>"
