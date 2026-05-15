"""Export route — generates a reviewable JSON or CSV export package per session.

GET /api/export/:sessionId              — generate and persist a new export (JSON)
GET /api/export/:sessionId?format=csv   — generate and download as CSV
GET /api/export/:sessionId/history      — list all past export packages for a session
"""
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/export", tags=["export"])


def _legacy_export_gone() -> None:
    raise HTTPException(
        status_code=410,
        detail="Legacy export routes are disabled. Use /api/workspaces/{workspace_id}/review-pack/* routes.",
    )


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def legacy_export_disabled(path: str):
    _legacy_export_gone()
