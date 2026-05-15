"""TaxItem model — classified line item from a document."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class TaxItem(Base):
    __tablename__ = "tax_items"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tax_sessions.id"), nullable=False
    )
    item_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="income / deduction / offset / needs_review"
    )
    category: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="e.g. salary_wages, tools_equipment"
    )
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    needs_review: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
        comment="True until user confirms or explicitly approves"
    )
    review_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="needs_review",
        comment="draft / needs_review / confirmed / excluded / tax_agent_review",
    )
    review_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Why this item needs review"
    )
    review_reason_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    encryption_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    key_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    ato_reference_hint: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
        comment="Optional ATO category reference (e.g. D1, D2, D3, D5)"
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reviewed_by: Mapped[str | None] = mapped_column(
        String(50), nullable=True, default="system"
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

    # Relationships
    session = relationship("TaxSession", back_populates="tax_items")
    source_documents = relationship(
        "DocumentItem", back_populates="tax_item", lazy="selectin"
    )

    def __repr__(self) -> str:
        return (
            f"<TaxItem id={self.id} type={self.item_type} "
            f"cat={self.category} needs_review={self.needs_review}>"
        )
