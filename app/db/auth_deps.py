from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.deps import get_db
from app.models.user import User
from app.services.auth.service import resolve_session, COOKIE_NAME, is_unlock_capability_active
from app.services.security.key_cache import get_session_key


def _extract_token(request: Request) -> str | None:
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", 1)[1].strip()
    return request.cookies.get(COOKIE_NAME)


def get_request_token(request: Request) -> str | None:
    return _extract_token(request)


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    token = _extract_token(request)
    user, _session = await resolve_session(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


async def get_optional_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User | None:
    token = _extract_token(request)
    user, _session = await resolve_session(db, token)
    return user


async def get_current_unlocked_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    token = _extract_token(request)
    user, auth_session = await resolve_session(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    if not auth_session:
        raise HTTPException(status_code=401, detail="Authentication required")
    if not await is_unlock_capability_active(db, user, auth_session, token):
        raise HTTPException(status_code=423, detail="Workspace is locked. Unlock to view sensitive tax data.")
    if not get_session_key(token):
        raise HTTPException(status_code=423, detail="Workspace is locked. Unlock to view sensitive tax data.")
    return user
