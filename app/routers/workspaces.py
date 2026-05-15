from datetime import datetime, timezone
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, Form, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.deps import get_db
from app.db.auth_deps import get_current_user
from app.db.workspace_scope import get_or_create_workspace_session, get_workspace_for_user, touch_workspace_opened
from app.models.document import Document
from app.models.tax_item import TaxItem
from app.models.user import User
from app.models.tax_workspace import TaxWorkspace
from app.schemas.workspace import WorkspaceCreateRequest, WorkspaceResponse
from app.services.auth.service import seed_default_workspaces
from app.services.compliance_review import run_compliance_review
from app.services.export import generate_export
from app.schemas.tax_item import WorkspaceReviewStatusUpdate, WorkspaceReviewSummaryResponse
from app.services.audit.writer import write_audit

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])
VALID_REVIEW_STATUSES = {"draft", "needs_review", "confirmed", "excluded", "tax_agent_review"}


def _to_response(ws: TaxWorkspace) -> WorkspaceResponse:
    return WorkspaceResponse(
        id=ws.id,
        user_id=ws.user_id,
        tax_year=ws.tax_year,
        label=ws.label,
        status=ws.status,
        created_at=ws.created_at.isoformat(),
        updated_at=ws.updated_at.isoformat(),
        last_opened_at=ws.last_opened_at.isoformat() if ws.last_opened_at else None,
    )


@router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await seed_default_workspaces(db, current_user.id)
    result = await db.execute(
        select(TaxWorkspace)
        .where(TaxWorkspace.user_id == current_user.id)
        .order_by(TaxWorkspace.tax_year.desc(), TaxWorkspace.created_at.desc())
    )
    workspaces = result.scalars().all()
    await db.commit()
    return [_to_response(ws) for ws in workspaces]


@router.post("", response_model=WorkspaceResponse)
async def create_workspace(
    payload: WorkspaceCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TaxWorkspace).where(
            TaxWorkspace.user_id == current_user.id,
            TaxWorkspace.tax_year == payload.tax_year,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Workspace for tax year already exists")

    ws = TaxWorkspace(
        user_id=current_user.id,
        tax_year=payload.tax_year,
        label=payload.label,
        status="active",
        last_opened_at=datetime.now(timezone.utc),
    )
    db.add(ws)
    await db.flush()
    await db.commit()
    await db.refresh(ws)
    return _to_response(ws)


@router.get("/{workspace_id}/documents")
async def list_workspace_documents(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspace = await get_workspace_for_user(db, current_user, workspace_id)
    session = await get_or_create_workspace_session(db, workspace)
    await touch_workspace_opened(workspace)
    result = await db.execute(
        select(Document).where(Document.session_id == session.id).order_by(Document.created_at.desc())
    )
    await db.commit()
    return result.scalars().all()


@router.post("/{workspace_id}/documents/upload")
async def upload_workspace_document(
    workspace_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    category: str | None = Form(default=None),
    financial_year: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Reuse existing upload behavior and OCR/classification pipeline unchanged.
    from app.routers.documents import upload_document_by_workspace

    return await upload_document_by_workspace(
        workspace_id=workspace_id,
        background_tasks=background_tasks,
        file=file,
        category=category,
        financial_year=financial_year,
        db=db,
        current_user=current_user,
    )


@router.get("/{workspace_id}/items")
async def list_workspace_items(
    workspace_id: str,
    review_status: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if review_status and review_status not in VALID_REVIEW_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid review_status filter")
    workspace = await get_workspace_for_user(db, current_user, workspace_id)
    session = await get_or_create_workspace_session(db, workspace)
    await touch_workspace_opened(workspace)
    stmt = select(TaxItem).where(TaxItem.session_id == session.id).order_by(TaxItem.created_at.desc())
    if review_status:
        stmt = stmt.where(TaxItem.review_status == review_status)
    result = await db.execute(stmt)
    await db.commit()
    return result.scalars().all()


@router.patch("/{workspace_id}/items/{item_id}/review-status")
async def set_workspace_item_review_status(
    workspace_id: str,
    item_id: str,
    payload: WorkspaceReviewStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.review_status not in {"needs_review", "confirmed", "excluded", "tax_agent_review"}:
        raise HTTPException(status_code=400, detail="Invalid review_status")

    workspace = await get_workspace_for_user(db, current_user, workspace_id)
    session = await get_or_create_workspace_session(db, workspace)
    await touch_workspace_opened(workspace)

    result = await db.execute(
        select(TaxItem).where(TaxItem.id == item_id, TaxItem.session_id == session.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    previous_status = item.review_status
    item.review_status = payload.review_status
    item.needs_review = payload.review_status in {"draft", "needs_review", "tax_agent_review"}
    item.review_reason = payload.note
    item.reviewed_at = datetime.now(timezone.utc)
    item.reviewed_by = "user"

    await write_audit(
        db,
        "tax_item",
        item.id,
        "review_status_updated",
        details={
            "from_status": previous_status,
            "to_status": payload.review_status,
            "has_note": bool(payload.note),
        },
    )
    await db.flush()
    await db.commit()
    await db.refresh(item)
    return item


@router.get("/{workspace_id}/review-summary", response_model=WorkspaceReviewSummaryResponse)
async def workspace_review_summary(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspace = await get_workspace_for_user(db, current_user, workspace_id)
    session = await get_or_create_workspace_session(db, workspace)
    await touch_workspace_opened(workspace)
    result = await db.execute(select(TaxItem).where(TaxItem.session_id == session.id))
    items = result.scalars().all()

    counts = {status: 0 for status in VALID_REVIEW_STATUSES}
    for item in items:
        status = item.review_status if item.review_status in counts else ("needs_review" if item.needs_review else "confirmed")
        counts[status] += 1

    blocking_reasons: list[str] = []
    if len(items) == 0:
        blocking_reasons.append("No review items available yet.")
    if counts["draft"] > 0:
        blocking_reasons.append(f"{counts['draft']} item(s) are still in draft.")
    if counts["needs_review"] > 0:
        blocking_reasons.append(f"{counts['needs_review']} item(s) still need review.")
    if counts["tax_agent_review"] > 0:
        blocking_reasons.append(f"{counts['tax_agent_review']} item(s) require tax agent review.")

    return WorkspaceReviewSummaryResponse(
        total_items=len(items),
        draft=counts["draft"],
        needs_review=counts["needs_review"],
        confirmed=counts["confirmed"],
        excluded=counts["excluded"],
        tax_agent_review=counts["tax_agent_review"],
        ready_for_export=len(blocking_reasons) == 0,
        blocking_reasons=blocking_reasons,
    )


@router.get("/{workspace_id}/issues")
async def list_workspace_issues(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspace = await get_workspace_for_user(db, current_user, workspace_id)
    session = await get_or_create_workspace_session(db, workspace)
    await touch_workspace_opened(workspace)
    return await run_compliance_review(db, session.id)


@router.post("/{workspace_id}/review-pack")
async def generate_workspace_review_pack(
    workspace_id: str,
    format: str = Query("json", pattern="^(json|csv)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspace = await get_workspace_for_user(db, current_user, workspace_id)
    session = await get_or_create_workspace_session(db, workspace)
    await touch_workspace_opened(workspace)
    pkg = await generate_export(db, session.id)
    if format == "json":
        return pkg
    from app.routers.export import _build_csv_response
    return _build_csv_response(session.id, pkg)
