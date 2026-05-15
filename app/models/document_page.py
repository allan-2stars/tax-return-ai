"""DocumentPage model — per-page OCR text and confidence.

Stores the extracted text and OCR confidence for each page of a document.
One Document → many DocumentPage rows.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class DocumentPage(Base):
    __tablename__ = "document_pages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id"), nullable=False
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    ocr_method: Mapped[str | None] = mapped_column(
        String(30), nullable=True, comment="pdfplumber / tesseract / identity"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship
    document = relationship("Document", back_populates="pages")

    def __repr__(self) -> str:
        return (
            f"<DocumentPage doc={self.document_id} "
            f"page={self.page_number} conf={self.confidence}>"
        )
