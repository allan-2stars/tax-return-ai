"""CRUD routes for tax items — including review actions and classification."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.deps import get_db
from app.db.auth_deps import get_current_user
from app.db.workspace_scope import (
    get_or_create_workspace_session,
    get_workspace_for_user,
    require_owned_item,
    require_owned_session,
    touch_workspace_opened,
)
from app.models.tax_item import TaxItem
from app.models.document import Document
from app.models.user import User
from app.schemas.tax_item import (
    TaxItemCreate,
    TaxItemUpdate,
    TaxItemResponse,
    TaxItemReview,
    BulkReviewRequest,
)
from app.schemas.classification import ClassificationRequest, ClassificationResponse
from app.services.audit.writer import write_audit
from app.services.classification import classify_document
from app.models.document_page import DocumentPage
from app.models.review_action import ReviewAction
from app.utils.sanitize import sanitize_description

router = APIRouter(prefix="/api/items", tags=["items"])


def _status_from_needs_review(needs_review: bool) -> str:
    return "needs_review" if needs_review else "confirmed"


@router.post("", response_model=TaxItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    data: TaxItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a tax item manually."""
    await require_owned_session(db, current_user, data.session_id)
    item = TaxItem(**data.model_dump())
    if not item.review_status:
        item.review_status = _status_from_needs_review(item.needs_review)
    db.add(item)
    await db.flush()
    await write_audit(db, "tax_item", item.id, "created")
    await db.commit()
    await db.refresh(item)
    return item


@router.post("/classify", response_model=list[ClassificationResponse], status_code=status.HTTP_201_CREATED)
async def classify_item(
    data: ClassificationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Classify extracted document text using the configured AI provider.

    Uses the mock provider by default (no API keys required).
    Set AI_PROVIDER=anthropic or AI_PROVIDER=openai in .env for real classification.

    - Low confidence (< 0.7) → needs_review=true always.
    - Creates one or more TaxItems and links them to the source document.
    - Returns a list of classification results — one per detected item/line.
    """
    # Verify document exists
    doc_result = await db.execute(
        select(Document).where(Document.id == data.document_id)
    )
    if not doc_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Document not found")

    # Use session's financial_year if not provided
    fy = data.financial_year
    if not fy:
        from app.models.tax_session import TaxSession
        sess_result = await db.execute(
            select(TaxSession).where(TaxSession.id == data.session_id)
        )
        session = sess_result.scalar_one_or_none()
        if session:
            fy = session.financial_year

    # Run classification — returns list of TaxItems
    items = await classify_document(
        db=db,
        document_id=data.document_id,
        session_id=data.session_id,
        extracted_text=data.extracted_text,
        financial_year=fy or "2025-2026",
        skill_context=data.skill_context,
    )

    return [
        ClassificationResponse(
            item_id=item.id,
            document_id=data.document_id,
            session_id=data.session_id,
            item_type=item.item_type,
            category=item.category,
            amount=item.amount,
            description=item.description,
            confidence=item.confidence,
            needs_review=item.needs_review,
            review_reason=item.review_reason,
            ato_reference_hint=item.ato_reference_hint,
        )
        for item in items
    ]


@router.get("", response_model=list[TaxItemResponse])
async def list_items(
    session_id: str | None = None,
    needs_review: bool | None = None,
    item_type: str | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(TaxItem)
        .order_by(TaxItem.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    if session_id:
        await require_owned_session(db, current_user, session_id)
        stmt = stmt.where(TaxItem.session_id == session_id)
    if needs_review is not None:
        stmt = stmt.where(TaxItem.needs_review == needs_review)
    if item_type:
        stmt = stmt.where(TaxItem.item_type == item_type)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{item_id}", response_model=TaxItemResponse)
async def get_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = await require_owned_item(db, current_user, item_id)
    return item


@router.patch("/{item_id}", response_model=TaxItemResponse)
async def update_item(
    item_id: str,
    data: TaxItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = await require_owned_item(db, current_user, item_id)
    update_data = data.model_dump(exclude_unset=True)
    if "description" in update_data:
        update_data["description"] = sanitize_description(update_data["description"])
    for field, value in update_data.items():
        setattr(item, field, value)
    await db.flush()
    await write_audit(db, "tax_item", item_id, "updated",
                      details={"fields": list(update_data.keys())})
    await db.commit()
    await db.refresh(item)
    return item


@router.post("/{item_id}/review", response_model=TaxItemResponse)
async def review_item(
    item_id: str,
    data: TaxItemReview,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark item as reviewed or flagged for review."""
    item = await require_owned_item(db, current_user, item_id)
    item.needs_review = data.needs_review
    item.review_status = _status_from_needs_review(data.needs_review)
    if data.review_reason == "excluded":
        item.review_status = "excluded"
        item.needs_review = False
    if data.review_reason == "tax_agent_review":
        item.review_status = "tax_agent_review"
        item.needs_review = True
    if data.review_reason:
        item.review_reason = data.review_reason
    item.reviewed_at = datetime.now(timezone.utc)
    item.reviewed_by = "user"

    # Determine status labels for the review action
    # (use the *new* data, not the already-updated item)
    previous_status = "approved" if data.needs_review else "flagged"
    new_status = "flagged" if data.needs_review else "approved"
    action_type = "user_corrected" if data.needs_review else "user_confirmed"

    # Write audit log
    await db.flush()
    action = "item_confirmed" if not data.needs_review else "flagged_for_review"
    if data.review_reason == "excluded":
        action = "item_excluded"
    if data.review_reason == "tax_agent_review":
        action = "item_tax_agent_review"
    await write_audit(db, "tax_item", item_id, action,
                      details=dict(needs_review=data.needs_review, reason=data.review_reason))

    # Record review action (append-only)
    review_action = ReviewAction(
        session_id=item.session_id,
        tax_item_id=item_id,
        action_type=action_type,
        previous_status=previous_status,
        new_status=new_status,
        notes=data.review_reason,
        changed_by="user",
    )
    db.add(review_action)

    await db.commit()
    await db.refresh(item)
    return item


@router.post("/bulk-review")
async def bulk_review_items(
    data: BulkReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Approve or flag multiple items at once."""
    count = 0
    for item_id in data.item_ids:
        result = await db.execute(select(TaxItem).where(TaxItem.id == item_id))
        item = result.scalar_one_or_none()
        if not item:
            continue
        await require_owned_session(db, current_user, item.session_id)

        previous = item.needs_review
        item.needs_review = data.needs_review
        item.review_status = _status_from_needs_review(data.needs_review)
        if data.review_reason:
            item.review_reason = data.review_reason
        item.reviewed_at = datetime.now(timezone.utc)
        item.reviewed_by = "user"

        action = ReviewAction(
            session_id=item.session_id,
            tax_item_id=item.id,
            action_type="user_confirmed" if not data.needs_review else "user_corrected",
            previous_status=str(previous),
            new_status=str(data.needs_review),
            notes=data.review_reason,
            changed_by="user",
        )
        db.add(action)
        count += 1

    await db.flush()
    await write_audit(db, "tax_item", "bulk", "bulk_reviewed",
                      details={"count": count, "needs_review": data.needs_review})
    await db.commit()

    return {"reviewed": count, "needs_review": data.needs_review}


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await require_owned_item(db, current_user, item_id)
    await db.execute(delete(TaxItem).where(TaxItem.id == item_id))
    await write_audit(db, "tax_item", item_id, "deleted")
    await db.commit()


@router.get("/workspaces/{workspace_id}/items", response_model=list[TaxItemResponse])
async def list_items_by_workspace(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspace = await get_workspace_for_user(db, current_user, workspace_id)
    session = await get_or_create_workspace_session(db, workspace)
    await touch_workspace_opened(workspace)
    result = await db.execute(
        select(TaxItem).where(TaxItem.session_id == session.id).order_by(TaxItem.created_at.desc())
    )
    await db.commit()
    return result.scalars().all()
