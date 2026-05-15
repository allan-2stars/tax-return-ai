"""DocumentItem — join table linking tax_items to their source documents."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class DocumentItem(Base):
    __tablename__ = "document_items"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id"), nullable=False
    )
    tax_item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tax_items.id"), nullable=False
    )
    page_number: Mapped[int | None] = mapped_column(
        nullable=True, comment="Source page in document"
    )
    snippet: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Excerpt from extracted text"
    )
    ocr_confidence: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    document = relationship("Document", back_populates="items")
    tax_item = relationship("TaxItem", back_populates="source_documents")

    def __repr__(self) -> str:
        return (
            f"<DocumentItem doc={self.document_id} "
            f"item={self.tax_item_id}>"
        )
