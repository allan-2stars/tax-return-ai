from fastapi import APIRouter, HTTPException


router = APIRouter(tags=["legacy"])


def _legacy_gone(message: str) -> None:
    raise HTTPException(status_code=410, detail=message)


@router.api_route("/api/export/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def legacy_export_disabled(path: str):
    _legacy_gone("Legacy export routes are disabled. Use /api/workspaces/{workspace_id}/review-pack/*.")


@router.api_route("/api/sessions/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def legacy_sessions_disabled(path: str):
    _legacy_gone("Legacy session routes are disabled. Use workspace-first /api/workspaces routes.")


@router.api_route("/api/documents/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def legacy_documents_disabled(path: str):
    _legacy_gone("Legacy document routes are disabled. Use /api/workspaces/{workspace_id}/documents routes.")


@router.api_route("/api/items/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def legacy_items_disabled(path: str):
    _legacy_gone("Legacy item routes are disabled. Use /api/workspaces/{workspace_id}/items routes.")


@router.api_route("/api/compliance/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def legacy_compliance_disabled(path: str):
    _legacy_gone("Legacy compliance routes are disabled. Use /api/workspaces/{workspace_id}/issues routes.")

