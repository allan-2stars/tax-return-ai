import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request

from app.models.user import User
from app.models.auth_session import AuthSession
from app.models.tax_workspace import TaxWorkspace

SESSION_TTL_HOURS = 12
COOKIE_NAME = "taxai_session"


def _as_utc(dt: datetime) -> datetime:
    """Normalize DB datetimes so SQLite naive values compare safely with UTC now."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8")


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _hash_with_pbkdf2(secret: str, salt_b64: str, iterations: int = 600_000) -> str:
    salt = base64.urlsafe_b64decode(salt_b64.encode("utf-8"))
    digest = hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt, iterations)
    return _b64(digest)


def _hash_with_argon2(secret: str, salt_b64: str) -> str:
    from argon2.low_level import hash_secret_raw, Type

    salt = base64.urlsafe_b64decode(salt_b64.encode("utf-8"))
    digest = hash_secret_raw(
        secret=secret.encode("utf-8"),
        salt=salt,
        time_cost=3,
        memory_cost=65536,
        parallelism=2,
        hash_len=32,
        type=Type.ID,
    )
    return _b64(digest)


def hash_secret(secret: str, salt_b64: str) -> tuple[str, str]:
    try:
        digest = _hash_with_argon2(secret, salt_b64)
        return "argon2id", digest
    except Exception:
        # fallback for Raspberry Pi environments where argon2 package may be unavailable
        digest = _hash_with_pbkdf2(secret, salt_b64)
        return "pbkdf2_sha256_600k", digest


def hash_secret_for_kdf(secret: str, salt_b64: str, kdf: str) -> str:
    if kdf == "argon2id":
        try:
            return _hash_with_argon2(secret, salt_b64)
        except Exception:
            # maintain unlock compatibility for fallback-only environments
            return _hash_with_pbkdf2(secret, salt_b64)
    return _hash_with_pbkdf2(secret, salt_b64)


def generate_recovery_key() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    raw = "".join(secrets.choice(alphabet) for _ in range(24))
    return f"{raw[:6]}-{raw[6:12]}-{raw[12:18]}-{raw[18:24]}"


async def get_active_user(db: AsyncSession) -> User | None:
    result = await db.execute(select(User).where(User.is_active == True))  # noqa: E712
    return result.scalars().first()


async def setup_user(
    db: AsyncSession,
    master_password: str,
    display_name: str | None,
    email: str | None,
    request: Request,
) -> tuple[User, str, str, datetime]:
    existing = await get_active_user(db)
    if existing:
        raise ValueError("Local user is already configured")

    password_salt = _b64(os.urandom(16))
    password_kdf, password_hash = hash_secret(master_password, password_salt)

    recovery_key = generate_recovery_key()
    recovery_salt = _b64(os.urandom(16))
    recovery_kdf, recovery_hash = hash_secret(recovery_key, recovery_salt)

    user = User(
        email=email,
        display_name=display_name,
        password_kdf=password_kdf,
        password_salt=password_salt,
        password_hash=password_hash,
        recovery_key_salt=recovery_salt,
        recovery_key_hash=recovery_hash,
        is_active=True,
        last_unlocked_at=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.flush()

    await seed_default_workspaces(db, user.id)

    token, expires_at = await create_session(db, user.id, request)
    return user, recovery_key, token, expires_at


async def seed_default_workspaces(db: AsyncSession, user_id: str) -> None:
    result = await db.execute(select(TaxWorkspace).where(TaxWorkspace.user_id == user_id))
    existing = result.scalars().all()
    if existing:
        return
    for fy in ("FY2025", "FY2024"):
        db.add(
            TaxWorkspace(
                user_id=user_id,
                tax_year=fy,
                label=f"{fy} Workspace",
                status="active",
                last_opened_at=datetime.now(timezone.utc),
            )
        )
    await db.flush()


async def verify_unlock(db: AsyncSession, master_password: str, request: Request) -> tuple[User, str, datetime]:
    user = await get_active_user(db)
    if not user:
        raise ValueError("Local user is not configured")

    candidate_hash = hash_secret_for_kdf(master_password, user.password_salt, user.password_kdf)
    if not hmac.compare_digest(candidate_hash, user.password_hash):
        raise PermissionError("Invalid master password")

    user.last_unlocked_at = datetime.now(timezone.utc)
    token, expires_at = await create_session(db, user.id, request)
    await db.flush()
    return user, token, expires_at


async def create_session(db: AsyncSession, user_id: str, request: Request) -> tuple[str, datetime]:
    token = secrets.token_urlsafe(48)
    token_hash = _sha256_hex(token)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=SESSION_TTL_HOURS)

    client_ip = request.client.host if request.client else ""
    ip_hash = _sha256_hex(client_ip) if client_ip else None
    user_agent = request.headers.get("user-agent")

    session = AuthSession(
        user_id=user_id,
        session_token_hash=token_hash,
        created_at=now,
        expires_at=expires_at,
        last_seen_at=now,
        user_agent=user_agent,
        ip_hash=ip_hash,
    )
    db.add(session)
    await db.flush()
    return token, expires_at


async def resolve_session(db: AsyncSession, token: str | None) -> tuple[User | None, AuthSession | None]:
    if not token:
        return None, None

    token_hash = _sha256_hex(token)
    result = await db.execute(select(AuthSession).where(AuthSession.session_token_hash == token_hash))
    auth_session = result.scalar_one_or_none()
    if not auth_session:
        return None, None

    now = datetime.now(timezone.utc)
    if auth_session.revoked_at is not None or _as_utc(auth_session.expires_at) <= now:
        return None, auth_session

    user_result = await db.execute(select(User).where(User.id == auth_session.user_id, User.is_active == True))  # noqa: E712
    user = user_result.scalar_one_or_none()
    if not user:
        return None, auth_session

    auth_session.last_seen_at = now
    await db.flush()
    return user, auth_session


async def revoke_session(db: AsyncSession, token: str | None) -> bool:
    if not token:
        return False
    token_hash = _sha256_hex(token)
    result = await db.execute(select(AuthSession).where(AuthSession.session_token_hash == token_hash))
    auth_session = result.scalar_one_or_none()
    if not auth_session:
        return False
    auth_session.revoked_at = datetime.now(timezone.utc)
    await db.flush()
    return True
