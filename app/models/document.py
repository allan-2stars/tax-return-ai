"""Document model — uploaded file metadata."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, DateTime, BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tax_sessions.id"), nullable=False
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    file_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="SHA-256 hex of original file"
    )
    storage_path: Mapped[str | None] = mapped_column(
        String(512), nullable=True, comment="Path to stored file"
    )
    extracted_text_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="SHA-256 of extracted text"
    )
    extraction_status: Mapped[str | None] = mapped_column(
        String(30), nullable=True, comment="pending / extracted / no_text / failed"
    )
    extraction_text_length: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Extracted text length in characters"
    )
    classification_status: Mapped[str | None] = mapped_column(
        String(30), nullable=True, comment="pending / classified / needs_review / failed / not_configured"
    )
    classification_provider: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="AI classification provider name"
    )
    classification_error: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Classification error summary"
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="uploaded",
        comment="uploaded / processing / processed / failed / needs_review"
    )
    status_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Failure reason or review note"
    )
    category: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Detected document type"
    )
    financial_year: Mapped[str | None] = mapped_column(
        String(9), nullable=True
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
    session = relationship("TaxSession", back_populates="documents")
    items = relationship("DocumentItem", back_populates="document", lazy="selectin")
    pages = relationship("DocumentPage", back_populates="document", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Document id={self.id} file={self.original_filename} status={self.status}>"
