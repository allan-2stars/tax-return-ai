from datetime import timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.deps import get_db
from app.config import settings
from app.db.auth_deps import get_optional_user
from app.schemas.auth import (
    SetupRequest,
    SetupResponse,
    SetupStatusResponse,
    UnlockRequest,
    SessionResponse,
    RecoveryResetRequest,
)
from app.services.auth.service import (
    COOKIE_NAME,
    get_active_user,
    setup_user,
    verify_unlock,
    recovery_reset_password,
    resolve_session,
    revoke_session,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _cookie_samesite() -> str:
    value = (settings.cookie_samesite or "lax").lower()
    if value not in {"lax", "strict", "none"}:
        return "lax"
    return value


def _cookie_secure() -> bool:
    if settings.cookie_secure:
        return True
    # insecure cookies are allowed only when explicitly enabled for local dev
    if settings.allow_insecure_cookie_local_dev:
        return False
    return True


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        secure=_cookie_secure(),
        samesite=_cookie_samesite(),
        domain=settings.cookie_domain or None,
        max_age=settings.effective_session_absolute_timeout_seconds,
        path="/",
    )


def _clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(
        COOKIE_NAME,
        path="/",
        domain=settings.cookie_domain or None,
        secure=_cookie_secure(),
        samesite=_cookie_samesite(),
        httponly=True,
    )


@router.get("/setup-status", response_model=SetupStatusResponse)
async def setup_status(db: AsyncSession = Depends(get_db)):
    user = await get_active_user(db)
    return SetupStatusResponse(
        is_configured=bool(user),
        has_active_user=bool(user),
    )


@router.post("/setup", response_model=SetupResponse)
async def setup_auth(
    payload: SetupRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    try:
        _user, recovery_key, token, expires_at = await setup_user(
            db,
            payload.master_password,
            payload.display_name,
            payload.email,
            request,
        )
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))

    _set_auth_cookie(response, token)
    return SetupResponse(recovery_key=recovery_key, app_state="UNLOCKED", session_token=token)


@router.post("/unlock")
async def unlock_auth(
    payload: UnlockRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    try:
        user, token, expires_at = await verify_unlock(db, payload.master_password, request)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    except PermissionError as exc:
        await db.rollback()
        raise HTTPException(status_code=401, detail=str(exc))

    _set_auth_cookie(response, token)
    return {
        "app_state": "UNLOCKED",
        "session_token": token,
        "expires_at": expires_at.isoformat(),
        "user_id": user.id,
        "display_name": user.display_name,
    }


@router.post("/recover-reset")
async def recover_reset_auth(
    payload: RecoveryResetRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    try:
        user, token, expires_at = await recovery_reset_password(
            db=db,
            recovery_key=payload.recovery_key,
            new_master_password=payload.new_master_password,
            request=request,
        )
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    except PermissionError as exc:
        await db.rollback()
        raise HTTPException(status_code=401, detail=str(exc))

    _set_auth_cookie(response, token)
    return {
        "app_state": "UNLOCKED",
        "session_token": token,
        "expires_at": expires_at.isoformat(),
        "user_id": user.id,
        "display_name": user.display_name,
    }


@router.post("/logout")
async def logout_auth(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    token = request.cookies.get(COOKIE_NAME)
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()

    await revoke_session(db, token)
    await db.commit()
    _clear_auth_cookie(response)
    return {"ok": True}


@router.get("/session", response_model=SessionResponse)
async def session_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    token = request.cookies.get(COOKIE_NAME)
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()

    user, auth_session = await resolve_session(db, token)
    await db.commit()

    if not token:
        return SessionResponse(is_authenticated=False, app_state="LOCKED")
    if not user:
        return SessionResponse(is_authenticated=False, app_state="SESSION_EXPIRED")

    expires_at = auth_session.expires_at.astimezone(timezone.utc).isoformat() if auth_session else None
    return SessionResponse(
        is_authenticated=True,
        app_state="UNLOCKED",
        user_id=user.id,
        display_name=user.display_name,
        expires_at=expires_at,
    )
