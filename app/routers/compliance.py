"""Compliance review route — runs ATO rules-based checks on a session.

GET /api/compliance/:sessionId
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.deps import get_db
from app.services.compliance_review import run_compliance_review

router = APIRouter(prefix="/api/compliance", tags=["compliance"])


@router.get("/{session_id}")
async def compliance_review(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Run a rules-based compliance review for all items in a session.

    Returns a structured ComplianceReviewResult matching the v1.1 schema.
    """
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
