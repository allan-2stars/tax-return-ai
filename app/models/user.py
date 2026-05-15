import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    password_kdf: Mapped[str] = mapped_column(String(40), nullable=False)
    password_salt: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    recovery_key_salt: Mapped[str] = mapped_column(String(255), nullable=False)
    recovery_key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_dek_by_password: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    encrypted_dek_by_recovery: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    dek_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    dek_wrapping_metadata: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    dek_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dek_rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    last_unlocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
