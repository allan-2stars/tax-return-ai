"""ReviewAction model — append-only log of user review actions on tax items."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class ReviewAction(Base):
    __tablename__ = "review_actions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tax_sessions.id"), nullable=False
    )
    tax_item_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tax_items.id"), nullable=True
    )
    action_type: Mapped[str] = mapped_column(
        String(30), nullable=False,
        comment="user_confirmed / user_corrected / user_excluded / agent_reviewed"
    )
    previous_status: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )
    new_status: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    changed_by: Mapped[str | None] = mapped_column(
        String(50), nullable=True, server_default="user"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<ReviewAction id={self.id} item={self.tax_item_id} "
            f"action={self.action_type}>"
        )
