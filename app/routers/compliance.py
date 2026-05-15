"""Compliance review route — runs ATO rules-based checks on a session.

GET /api/compliance/:sessionId
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.deps import get_db
from app.db.auth_deps import get_current_user
from app.db.workspace_scope import (
    get_or_create_workspace_session,
    get_workspace_for_user,
    require_owned_session,
    touch_workspace_opened,
)
from app.models.user import User
from app.services.compliance_review import run_compliance_review

router = APIRouter(prefix="/api/compliance", tags=["compliance"])


@router.get("/{session_id}")
async def compliance_review(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run a rules-based compliance review for all items in a session.

    Returns a structured ComplianceReviewResult matching the v1.1 schema.
    """
    await require_owned_session(db, current_user, session_id)
    try:
        result = await run_compliance_review(db, session_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Compliance review failed: {str(e)}",
        )


@router.get("/workspaces/{workspace_id}/issues")
async def compliance_review_by_workspace(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspace = await get_workspace_for_user(db, current_user, workspace_id)
    session = await get_or_create_workspace_session(db, workspace)
    await touch_workspace_opened(workspace)
    return await compliance_review(session.id, db=db, current_user=current_user)
