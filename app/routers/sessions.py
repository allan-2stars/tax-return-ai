"""CRUD routes for tax sessions."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.deps import get_db
from app.models.tax_session import TaxSession
from app.models.document import Document
from app.models.tax_item import TaxItem
from app.schemas.tax_session import TaxSessionCreate, TaxSessionUpdate, TaxSessionResponse
from app.services.audit.writer import write_audit
from app.utils.sanitize import sanitize_session_title

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=TaxSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(data: TaxSessionCreate, db: AsyncSession = Depends(get_db)):
    session = TaxSession(**data.model_dump())
    session.title = sanitize_session_title(session.title)
    db.add(session)
    await db.flush()
    await write_audit(db, "tax_session", session.id, "created")
    await db.commit()
    await db.refresh(session)
    return session


@router.get("", response_model=list[TaxSessionResponse])
async def list_sessions(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TaxSession)
        .order_by(TaxSession.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/{session_id}", response_model=TaxSessionResponse)
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TaxSession).where(TaxSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/{session_id}/stats")
async def get_session_stats(session_id: str, db: AsyncSession = Depends(get_db)):
    """Get document and item counts for a session."""
    # Verify session exists
    result = await db.execute(select(TaxSession).where(TaxSession.id == session_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Session not found")

    # Count documents
    doc_total = (
        await db.execute(
            select(func.count(Document.id)).where(Document.session_id == session_id)
        )
    ).scalar() or 0

    # Count classified documents
    classified_total = (
        await db.execute(
            select(func.count(Document.id)).where(
                Document.session_id == session_id,
                Document.status == "classified",
            )
        )
    ).scalar() or 0

    # Count items by type
    income_total = (
        await db.execute(
            select(func.count(TaxItem.id)).where(
                TaxItem.session_id == session_id,
                TaxItem.item_type == "income",
            )
        )
    ).scalar() or 0

    deduction_total = (
        await db.execute(
            select(func.count(TaxItem.id)).where(
                TaxItem.session_id == session_id,
                TaxItem.item_type == "deduction",
            )
        )
    ).scalar() or 0

    needs_review_total = (
        await db.execute(
            select(func.count(TaxItem.id)).where(
                TaxItem.session_id == session_id,
                TaxItem.needs_review == True,  # noqa: E712
            )
        )
    ).scalar() or 0

    return {
        "session_id": session_id,
        "document_count": doc_total,
        "classified_document_count": classified_total,
        "income_item_count": income_total,
        "deduction_item_count": deduction_total,
        "needs_review_item_count": needs_review_total,
        "total_item_count": income_total + deduction_total,
    }


@router.patch("/{session_id}", response_model=TaxSessionResponse)
async def update_session(
    session_id: str, data: TaxSessionUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(TaxSession).where(TaxSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    update_data = data.model_dump(exclude_unset=True)
    if "title" in update_data:
        update_data["title"] = sanitize_session_title(update_data["title"])
    for field, value in update_data.items():
        setattr(session, field, value)
    await db.flush()
    await write_audit(db, "tax_session", session_id, "updated", details={"fields": list(update_data.keys())})
    await db.commit()
    await db.refresh(session)
    return session


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TaxSession).where(TaxSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await db.execute(delete(TaxSession).where(TaxSession.id == session_id))
    await write_audit(db, "tax_session", session_id, "deleted")
    await db.commit()
