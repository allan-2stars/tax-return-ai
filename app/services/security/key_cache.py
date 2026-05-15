from __future__ import annotations

import hashlib
from datetime import datetime, timezone


_SESSION_KEYS: dict[str, tuple[str, bytes, datetime]] = {}


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def cache_session_key(token: str, user_id: str, key: bytes, expires_at: datetime) -> None:
    _SESSION_KEYS[_token_hash(token)] = (user_id, key, expires_at)


def get_session_key(token: str | None) -> bytes | None:
    if not token:
        return None
    row = _SESSION_KEYS.get(_token_hash(token))
    if not row:
        return None
    _user_id, key, expires_at = row
    now = datetime.now(timezone.utc)
    exp = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=timezone.utc)
    if exp <= now:
        _SESSION_KEYS.pop(_token_hash(token), None)
        return None
    return key


def get_session_key_by_hash(token_hash: str | None) -> bytes | None:
    if not token_hash:
        return None
    row = _SESSION_KEYS.get(token_hash)
    if not row:
        return None
    _user_id, key, expires_at = row
    now = datetime.now(timezone.utc)
    exp = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=timezone.utc)
    if exp <= now:
        _SESSION_KEYS.pop(token_hash, None)
        return None
    return key


def get_user_active_key(user_id: str) -> bytes | None:
    now = datetime.now(timezone.utc)
    for token_hash, row in list(_SESSION_KEYS.items()):
        row_user, key, expires_at = row
        exp = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=timezone.utc)
        if exp <= now:
            _SESSION_KEYS.pop(token_hash, None)
            continue
        if row_user == user_id:
            return key
    return None


def clear_session_key(token: str | None) -> None:
    if not token:
        return
    _SESSION_KEYS.pop(_token_hash(token), None)
