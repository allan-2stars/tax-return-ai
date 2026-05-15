"""ExportPackage model — generated review package metadata."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class ExportPackageModel(Base):
    __tablename__ = "export_packages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tax_sessions.id"), nullable=False
    )
    workspace_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tax_workspaces.id"), nullable=True
    )
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="ready")
    format: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="json",
        comment="json / csv / pdf"
    )
    encrypted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    kdf: Mapped[str | None] = mapped_column(String(40), nullable=True)
    downloaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    document_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    blocking_reasons: Mapped[str | None] = mapped_column(Text, nullable=True)
    storage_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    item_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    total_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_taxable: Mapped[float | None] = mapped_column(Float, nullable=True)
    compliance_score: Mapped[str | None] = mapped_column(
        String(10), nullable=True,
        comment="low / medium / high"
    )
    export_data: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Full JSON export payload"
    )
    exported_by: Mapped[str | None] = mapped_column(
        String(50), nullable=True, server_default="system"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<ExportPackageModel id={self.id} session={self.session_id} "
            f"format={self.format} items={self.item_count}>"
        )
