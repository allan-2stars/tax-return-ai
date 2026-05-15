from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.tax_item import TaxItem
from app.models.tax_session import TaxSession
from app.models.tax_workspace import TaxWorkspace
from app.models.user import User


def _fy_to_financial_year(tax_year: str) -> str:
    """Map FY2025 -> 2024-2025 (Australian FY end-year notation)."""
    if tax_year.startswith("FY") and tax_year[2:].isdigit():
        end_year = int(tax_year[2:])
        return f"{end_year - 1}-{end_year}"
    return "2025-2026"


async def get_workspace_for_user(db: AsyncSession, user: User, workspace_id: str) -> TaxWorkspace:
    result = await db.execute(
        select(TaxWorkspace).where(
            TaxWorkspace.id == workspace_id,
            TaxWorkspace.user_id == user.id,
        )
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


async def get_or_create_workspace_session(db: AsyncSession, workspace: TaxWorkspace) -> TaxSession:
    result = await db.execute(
        select(TaxSession).where(TaxSession.workspace_id == workspace.id).order_by(TaxSession.created_at.desc())
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    session = TaxSession(
        workspace_id=workspace.id,
        title=f"{workspace.label} Session",
        financial_year=_fy_to_financial_year(workspace.tax_year),
        status="draft",
        notes="Auto-created bridge session for workspace-scoped API.",
    )
    db.add(session)
    await db.flush()
    return session


async def require_owned_session(
    db: AsyncSession,
    user: User,
    session_id: str,
) -> TaxSession:
    result = await db.execute(select(TaxSession).where(TaxSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.workspace_id:
        workspace = await get_workspace_for_user(db, user, session.workspace_id)
        return session

    # Legacy bridge: try to associate legacy session to user workspace by FY.
    ws_result = await db.execute(
        select(TaxWorkspace)
        .where(TaxWorkspace.user_id == user.id)
        .order_by(TaxWorkspace.created_at.asc())
    )
    workspaces = ws_result.scalars().all()
    if not workspaces:
        raise HTTPException(status_code=404, detail="Session not found")

    # Prefer tax-year match when possible.
    mapped = None
    for ws in workspaces:
        if _fy_to_financial_year(ws.tax_year) == session.financial_year:
            mapped = ws
            break
    if mapped is None:
        mapped = workspaces[0]
    session.workspace_id = mapped.id
    await db.flush()
    return session


async def require_owned_document(db: AsyncSession, user: User, document_id: str) -> Document:
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    await require_owned_session(db, user, doc.session_id)
    return doc


async def require_owned_item(db: AsyncSession, user: User, item_id: str) -> TaxItem:
    result = await db.execute(select(TaxItem).where(TaxItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    await require_owned_session(db, user, item.session_id)
    return item


async def touch_workspace_opened(workspace: TaxWorkspace) -> None:
    workspace.last_opened_at = datetime.now(timezone.utc)
