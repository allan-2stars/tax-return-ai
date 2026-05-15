from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.auth_session import AuthSession
from app.models.unlock_capability import UnlockCapability
from app.models.user import User

_CAPABILITY_METRICS = {
    "locked_or_missing": 0,
    "stale_epoch": 0,
    "revoked": 0,
    "expired": 0,
}


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _capability_ttl_seconds() -> int:
    default_ttl = min(settings.effective_session_idle_timeout_seconds, 900)
    return max(60, default_ttl)


async def issue_unlock_capability(
    db: AsyncSession,
    user: User,
    session: AuthSession,
    session_token_hash: str,
) -> UnlockCapability:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=_capability_ttl_seconds())

    result = await db.execute(
        select(UnlockCapability).where(UnlockCapability.session_token_hash == session_token_hash)
    )
    capability = result.scalar_one_or_none()
    if capability:
        capability.user_id = user.id
        capability.auth_session_id = session.id
        capability.key_epoch = user.unlock_epoch
        capability.expires_at = expires_at
        capability.last_seen_at = now
        capability.revoked_at = None
        return capability

    capability = UnlockCapability(
        user_id=user.id,
        auth_session_id=session.id,
        session_token_hash=session_token_hash,
        key_epoch=user.unlock_epoch,
        expires_at=expires_at,
        last_seen_at=now,
    )
    db.add(capability)
    await db.flush()
    return capability


async def validate_unlock_capability(
    db: AsyncSession,
    user: User,
    auth_session: AuthSession,
    session_token_hash: str,
    touch: bool = True,
) -> bool:
    result = await db.execute(
        select(UnlockCapability).where(UnlockCapability.session_token_hash == session_token_hash)
    )
    capability = result.scalar_one_or_none()
    if not capability:
        _CAPABILITY_METRICS["locked_or_missing"] += 1
        return False

    now = datetime.now(timezone.utc)
    if capability.user_id != user.id or capability.auth_session_id != auth_session.id:
        _CAPABILITY_METRICS["revoked"] += 1
        return False
    if capability.revoked_at is not None:
        _CAPABILITY_METRICS["revoked"] += 1
        return False
    if _as_utc(capability.expires_at) <= now:
        _CAPABILITY_METRICS["expired"] += 1
        return False
    if user.unlock_epoch != capability.key_epoch or auth_session.key_epoch != capability.key_epoch:
        _CAPABILITY_METRICS["stale_epoch"] += 1
        return False

    if touch:
        capability.last_seen_at = now
        capability.expires_at = now + timedelta(seconds=_capability_ttl_seconds())
        await db.flush()
    return True


async def revoke_capability_for_session(db: AsyncSession, session_token_hash: str, revoked_at: datetime | None = None) -> None:
    result = await db.execute(
        select(UnlockCapability).where(UnlockCapability.session_token_hash == session_token_hash)
    )
    capability = result.scalar_one_or_none()
    if capability:
        capability.revoked_at = revoked_at or datetime.now(timezone.utc)
        await db.flush()


async def revoke_capabilities_for_user(db: AsyncSession, user_id: str, revoked_at: datetime | None = None) -> int:
    now = revoked_at or datetime.now(timezone.utc)
    result = await db.execute(
        select(UnlockCapability).where(UnlockCapability.user_id == user_id, UnlockCapability.revoked_at.is_(None))
    )
    rows = result.scalars().all()
    for row in rows:
        row.revoked_at = now
    await db.flush()
    return len(rows)


def get_capability_metrics() -> dict[str, int]:
    return dict(_CAPABILITY_METRICS)
