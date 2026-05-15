"""Export route — generates a reviewable JSON or CSV export package per session.

GET /api/export/:sessionId              — generate and persist a new export (JSON)
GET /api/export/:sessionId?format=csv   — generate and download as CSV
GET /api/export/:sessionId/history      — list all past export packages for a session
"""
import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.deps import get_db
from app.config import settings
from app.db.auth_deps import get_current_user
from app.db.workspace_scope import (
    get_or_create_workspace_session,
    get_workspace_for_user,
    require_owned_session,
    touch_workspace_opened,
)
from app.models.export_package import ExportPackageModel
from app.models.user import User
from app.schemas.export import ExportPackageRecord
from app.services.export import generate_export

router = APIRouter(prefix="/api/export", tags=["export"])


def _ensure_legacy_enabled() -> None:
    if not settings.enable_legacy_export_routes:
        raise HTTPException(status_code=410, detail="Legacy export routes are disabled. Use workspace review-pack routes.")


@router.get("/{session_id}")
async def export_session(
    session_id: str,
    format: str = Query("json", pattern="^(json|csv)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a reviewable export package for the session.

    By default returns JSON. Pass ?format=csv to download as CSV.
    Also persists a record to the export_packages table.
    """
    _ensure_legacy_enabled()
    await require_owned_session(db, current_user, session_id)
    try:
        pkg = await generate_export(db, session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Export generation failed: {str(e)}",
        )

    if format == "csv":
        return _build_csv_response(session_id, pkg)

    return pkg


def _build_csv_response(session_id: str, pkg: dict) -> StreamingResponse:
    """Convert an ExportPackage dict into a CSV download response."""
    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    writer.writerow(["Type", "Category", "Description", "Amount", "Status"])

    # Write income items
    for item in pkg.get("income_items", []):
        writer.writerow([
            "Income",
            item.get("category", ""),
            item.get("description", ""),
            item.get("amount", ""),
            "approved" if not item.get("needs_review") else "review",
        ])

    # Write deduction items
    for item in pkg.get("deduction_items", []):
        writer.writerow([
            "Deduction",
            item.get("category", ""),
            item.get("description", ""),
            item.get("amount", ""),
            "approved" if not item.get("needs_review") else "review",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=export-{session_id[:8]}.csv",
        },
    )


@router.get("/{session_id}/history", response_model=list[ExportPackageRecord])
async def export_history(
    session_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all export packages for a session, ordered by newest first."""
    _ensure_legacy_enabled()
    await require_owned_session(db, current_user, session_id)
    result = await db.execute(
        select(ExportPackageModel)
        .where(ExportPackageModel.session_id == session_id)
        .order_by(ExportPackageModel.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    records = result.scalars().all()
    return records


@router.post("/workspaces/{workspace_id}/review-pack")
async def export_workspace_review_pack(
    workspace_id: str,
    format: str = Query("json", pattern="^(json|csv)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_legacy_enabled()
    workspace = await get_workspace_for_user(db, current_user, workspace_id)
    session = await get_or_create_workspace_session(db, workspace)
    await touch_workspace_opened(workspace)
    return await export_session(session.id, format=format, db=db, current_user=current_user)
