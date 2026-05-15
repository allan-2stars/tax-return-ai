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
from app.models.export_package import ExportPackageModel
from app.schemas.export import ExportPackageRecord
from app.services.export import generate_export

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/{session_id}")
async def export_session(
    session_id: str,
    format: str = Query("json", pattern="^(json|csv)$"),
    db: AsyncSession = Depends(get_db),
):
    """Generate a reviewable export package for the session.

    By default returns JSON. Pass ?format=csv to download as CSV.
    Also persists a record to the export_packages table.
    """
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
):
    """Return all export packages for a session, ordered by newest first."""
    result = await db.execute(
        select(ExportPackageModel)
        .where(ExportPackageModel.session_id == session_id)
        .order_by(ExportPackageModel.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    records = result.scalars().all()
    return records
