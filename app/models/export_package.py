"""ExportPackage model — generated review package metadata.

Stores metadata and the full JSON export payload for each export operation.
One session can have multiple export packages over time.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, Float, DateTime, ForeignKey
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
    format: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="json",
        comment="json / csv / pdf"
    )
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
