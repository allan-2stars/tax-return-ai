import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request

from app.config import settings
from app.models.user import User
from app.models.auth_session import AuthSession
from app.models.tax_workspace import TaxWorkspace
from app.services.audit.writer import write_audit
from app.services.security.key_cache import cache_session_key, clear_session_key, clear_session_key_by_hash, clear_user_keys
from app.services.security.unlock_capability import (
    issue_unlock_capability,
    revoke_capabilities_for_user,
    revoke_capability_for_session,
    validate_unlock_capability,
)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

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


def derive_field_encryption_key(master_password: str, password_salt_b64: str, password_kdf: str) -> bytes:
    """Derive 32-byte field encryption key from master password and existing auth KDF material."""
    verifier = hash_secret_for_kdf(master_password, password_salt_b64, password_kdf)
    raw = base64.urlsafe_b64decode(verifier.encode("utf-8"))
    return hashlib.sha256(raw + b":field-encryption:v1").digest()


def _derive_kek(secret: str, salt_b64: str, kdf: str) -> bytes:
    raw = base64.urlsafe_b64decode(hash_secret_for_kdf(secret, salt_b64, kdf).encode("utf-8"))
    return hashlib.sha256(raw + b":dek-wrap:v1").digest()


def _wrap_dek(dek: bytes, kek: bytes, key_version: str) -> str:
    nonce = os.urandom(12)
    ct = AESGCM(kek).encrypt(nonce, dek, None)
    payload = {
        "version": "dek_wrapped_v1",
        "alg": "AES-256-GCM",
        "nonce": _b64(nonce),
        "ciphertext": _b64(ct),
        "key_version": key_version,
    }
    return "wrap::" + json.dumps(payload, separators=(",", ":"), ensure_ascii=True)


def _unwrap_dek(wrapped: str, kek: bytes) -> bytes:
    if not wrapped.startswith("wrap::"):
        raise ValueError("Invalid wrapped DEK format")
    payload = json.loads(wrapped[len("wrap::") :])
    nonce = base64.urlsafe_b64decode(payload["nonce"].encode("utf-8"))
    ct = base64.urlsafe_b64decode(payload["ciphertext"].encode("utf-8"))
    return AESGCM(kek).decrypt(nonce, ct, None)


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


def verify_hash_any_kdf(secret: str, salt_b64: str, expected_hash: str) -> tuple[bool, str]:
    for kdf in ("argon2id", "pbkdf2_sha256_600k"):
        candidate = hash_secret_for_kdf(secret, salt_b64, kdf)
        if hmac.compare_digest(candidate, expected_hash):
            return True, kdf
    return False, "pbkdf2_sha256_600k"


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

    dek = os.urandom(32)
    password_kek = _derive_kek(master_password, password_salt, password_kdf)
    recovery_kek = _derive_kek(recovery_key, recovery_salt, recovery_kdf)
    wrapped_by_password = _wrap_dek(dek, password_kek, "password_kek_v1")
    wrapped_by_recovery = _wrap_dek(dek, recovery_kek, "recovery_kek_v1")

    user = User(
        email=email,
        display_name=display_name,
        password_kdf=password_kdf,
        password_salt=password_salt,
        password_hash=password_hash,
        recovery_key_salt=recovery_salt,
        recovery_key_hash=recovery_hash,
        encrypted_dek_by_password=wrapped_by_password,
        encrypted_dek_by_recovery=wrapped_by_recovery,
        dek_version="dek_wrapped_v1",
        dek_wrapping_metadata=json.dumps({"scheme": "password+recovery"}, separators=(",", ":")),
        dek_created_at=datetime.now(timezone.utc),
        is_active=True,
        last_unlocked_at=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.flush()

    await seed_default_workspaces(db, user.id)

    token, expires_at = await create_session(db, user.id, request)
    session_token_hash = _sha256_hex(token)
    session_row = await _get_session_by_hash(db, session_token_hash)
    if session_row:
        await issue_unlock_capability(db, user, session_row, session_token_hash)
    cache_session_key(token, user.id, dek, expires_at)
    await write_audit(db, "user", user.id, "workspace_unlocked", details={"reason": "initial_setup"})
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
    session_token_hash = _sha256_hex(token)
    if user.encrypted_dek_by_password:
        password_kek = _derive_kek(master_password, user.password_salt, user.password_kdf)
        dek = _unwrap_dek(user.encrypted_dek_by_password, password_kek)
    else:
        # Backward compatibility: bootstrap from legacy password-derived key.
        dek = derive_field_encryption_key(master_password, user.password_salt, user.password_kdf)
        password_kek = _derive_kek(master_password, user.password_salt, user.password_kdf)
        user.encrypted_dek_by_password = _wrap_dek(dek, password_kek, "password_kek_v1")
        user.dek_version = "legacy_password_derived"
        user.dek_wrapping_metadata = json.dumps({"scheme": "password_only_bootstrap"}, separators=(",", ":"))
        user.dek_created_at = user.dek_created_at or datetime.now(timezone.utc)
    cache_session_key(token, user.id, dek, expires_at)
    session_row = await _get_session_by_hash(db, session_token_hash)
    if session_row:
        await issue_unlock_capability(db, user, session_row, session_token_hash)
    await write_audit(db, "user", user.id, "workspace_unlocked", details={"reason": "manual_unlock"})
    await db.flush()
    return user, token, expires_at


async def recovery_reset_password(
    db: AsyncSession,
    recovery_key: str,
    new_master_password: str,
    request: Request,
) -> tuple[User, str, datetime]:
    user = await get_active_user(db)
    if not user:
        raise ValueError("Local user is not configured")

    recovery_ok, recovery_kdf = verify_hash_any_kdf(recovery_key, user.recovery_key_salt, user.recovery_key_hash)
    if not recovery_ok:
        raise PermissionError("Invalid recovery key")
    if not user.encrypted_dek_by_recovery:
        raise ValueError("Recovery reset unavailable for this account")

    recovery_kek = _derive_kek(recovery_key, user.recovery_key_salt, recovery_kdf)
    dek = _unwrap_dek(user.encrypted_dek_by_recovery, recovery_kek)

    new_password_salt = _b64(os.urandom(16))
    new_password_kdf, new_password_hash = hash_secret(new_master_password, new_password_salt)
    new_password_kek = _derive_kek(new_master_password, new_password_salt, new_password_kdf)

    user.password_salt = new_password_salt
    user.password_kdf = new_password_kdf
    user.password_hash = new_password_hash
    user.encrypted_dek_by_password = _wrap_dek(dek, new_password_kek, "password_kek_v1")
    user.dek_rotated_at = datetime.now(timezone.utc)
    user.last_unlocked_at = datetime.now(timezone.utc)
    user.unlock_epoch = (user.unlock_epoch or 1) + 1
    revoke_result = await db.execute(
        select(AuthSession).where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))
    )
    for row in revoke_result.scalars().all():
        row.revoked_at = datetime.now(timezone.utc)
    await revoke_capabilities_for_user(db, user.id, revoked_at=datetime.now(timezone.utc))
    clear_user_keys(user.id)

    token, expires_at = await create_session(db, user.id, request)
    session_token_hash = _sha256_hex(token)
    session_row = await _get_session_by_hash(db, session_token_hash)
    if session_row:
        await issue_unlock_capability(db, user, session_row, session_token_hash)
    cache_session_key(token, user.id, dek, expires_at)
    await write_audit(db, "user", user.id, "recovery_reset_completed")
    await write_audit(db, "user", user.id, "workspace_unlocked", details={"reason": "recovery_reset"})
    await db.flush()
    return user, token, expires_at


async def create_session(db: AsyncSession, user_id: str, request: Request) -> tuple[str, datetime]:
    token = secrets.token_urlsafe(48)
    token_hash = _sha256_hex(token)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=settings.effective_session_absolute_timeout_seconds)

    client_ip = request.client.host if request.client else ""
    ip_hash = _sha256_hex(client_ip) if client_ip else None
    user_agent = request.headers.get("user-agent")

    user_result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))  # noqa: E712
    user = user_result.scalar_one_or_none()
    key_epoch = user.unlock_epoch if user else 1
    session = AuthSession(
        user_id=user_id,
        session_token_hash=token_hash,
        key_epoch=key_epoch,
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
        await write_audit(
            db,
            "auth_session",
            token_hash[:36],
            "invalid_session_token",
            details={"reason": "session_not_found"},
        )
        return None, None

    now = datetime.now(timezone.utc)
    created_at = _as_utc(auth_session.created_at)
    last_seen_at = _as_utc(auth_session.last_seen_at)
    expires_at = _as_utc(auth_session.expires_at)
    idle_cutoff = timedelta(seconds=settings.effective_session_idle_timeout_seconds)
    absolute_cutoff = timedelta(seconds=settings.effective_session_absolute_timeout_seconds)
    idle_expired = now - last_seen_at >= idle_cutoff
    absolute_expired = now - created_at >= absolute_cutoff
    expired = expires_at <= now or idle_expired or absolute_expired
    if auth_session.revoked_at is not None or expired:
        clear_session_key(token)
        clear_session_key_by_hash(auth_session.session_token_hash)
        await revoke_capability_for_session(db, auth_session.session_token_hash, revoked_at=now)
        if expired and auth_session.revoked_at is None:
            auth_session.revoked_at = now
            await write_audit(
                db,
                "user",
                auth_session.user_id,
                "auto_lock_triggered" if idle_expired else "session_expired",
                details={
                    "idle_timeout_seconds": settings.effective_session_idle_timeout_seconds,
                    "absolute_timeout_seconds": settings.effective_session_absolute_timeout_seconds,
                },
            )
            await write_audit(
                db,
                "user",
                auth_session.user_id,
                "workspace_locked",
                details={"reason": "session_expired"},
            )
        return None, auth_session

    user_result = await db.execute(select(User).where(User.id == auth_session.user_id, User.is_active == True))  # noqa: E712
    user = user_result.scalar_one_or_none()
    if not user:
        return None, auth_session
    if user.unlock_epoch != auth_session.key_epoch:
        auth_session.revoked_at = now
        await revoke_capability_for_session(db, auth_session.session_token_hash, revoked_at=now)
        clear_session_key(token)
        clear_session_key_by_hash(auth_session.session_token_hash)
        await write_audit(
            db,
            "user",
            user.id,
            "session_expired",
            details={"reason": "stale_key_epoch"},
        )
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
    await write_audit(
        db,
        "user",
        auth_session.user_id,
        "workspace_locked",
        details={"reason": "manual_logout"},
    )
    await revoke_capability_for_session(db, auth_session.session_token_hash)
    clear_session_key(token)
    clear_session_key_by_hash(auth_session.session_token_hash)
    await db.flush()
    return True


async def _get_session_by_hash(db: AsyncSession, session_token_hash: str) -> AuthSession | None:
    result = await db.execute(select(AuthSession).where(AuthSession.session_token_hash == session_token_hash))
    return result.scalar_one_or_none()


async def is_unlock_capability_active(
    db: AsyncSession,
    user: User,
    auth_session: AuthSession,
    token: str,
) -> bool:
    token_hash = _sha256_hex(token)
    return await validate_unlock_capability(db, user, auth_session, token_hash, touch=True)
