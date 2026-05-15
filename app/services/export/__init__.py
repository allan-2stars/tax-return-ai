"""Export service — generates the review package JSON for a session.

The frontend ExportButton calls GET /api/export/:sessionId and expects
the ExportPackage shape defined in frontend/lib/api.ts.

Now also persists a record to the export_packages table.
"""
import json
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.tax_session import TaxSession
from app.models.document import Document
from app.models.tax_item import TaxItem
from app.models.export_package import ExportPackageModel
from app.services.audit.writer import write_audit


@dataclass
class ExportPackage:
    """The full export package returned to the frontend."""

    export_metadata: dict
    session: dict
    summary: dict
    income_items: list = field(default_factory=list)
    deduction_items: list = field(default_factory=list)
    needs_review_items: list = field(default_factory=list)
    out_of_scope_items: list = field(default_factory=list)
    source_documents: list = field(default_factory=list)
    export_warnings: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ── ATO category reference hints for compliance warnings ────────────────────
_ATO_HIGH_RISK_CATEGORIES = {
    "work_from_home": "D5 — Home office expenses (ATO scrutiny risk)",
    "tools_equipment": "D5 — Equipment under $300 or decline in value",
    "mixed_use": "Mixed-use items require personal-use apportionment",
    "donation": "D15 — Donations require receipt evidence",
    "union_fee": "D5 — Union fees (low risk)",
    "subscription": "D5 — Professional subscriptions (low risk)",
    "other": "D5/Other — Review ATO guidance for this category",
}


def _item_to_json(item: TaxItem) -> dict:
    """Serialize a TaxItem to the frontend's expected shape."""
    return {
        "id": item.id,
        "category": item.category,
        "amount": item.amount,
        "description": item.description or "",
        "confidence": item.confidence or 0.0,
        "needs_review": item.needs_review,
        "review_reason": item.review_reason,
        "ato_reference_hint": item.ato_reference_hint,
    }


async def generate_export(
    db: AsyncSession,
    session_id: str,
) -> dict:
    """Generate a complete review package for a session.

    Steps:
    1. Load session + documents + items
    2. Categorise items into income / deduction / needs_review / out_of_scope
    3. Compute summary statistics
    4. Generate compliance warnings
    5. Return everything as a dict matching the frontend ExportPackage type
    """
    # Load session
    result = await db.execute(select(TaxSession).where(TaxSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise ValueError(f"Session not found: {session_id}")

    # Load documents
    result = await db.execute(
        select(Document).where(Document.session_id == session_id)
    )
    documents = result.scalars().all()

    # Load items
    result = await db.execute(
        select(TaxItem).where(TaxItem.session_id == session_id)
    )
    items = result.scalars().all()

    # Categorise
    income_items = [i for i in items if i.item_type == "income"]
    deduction_items = [i for i in items if i.item_type == "deduction"]
    out_of_scope_items = [i for i in items if i.item_type == "out_of_scope"]
    needs_review_items = [i for i in items if i.needs_review]

    # Summary
    total_income = sum(i.amount or 0 for i in income_items)
    total_deductions = sum(i.amount or 0 for i in deduction_items)
    approved_items = [i for i in items if not i.needs_review]

    # Compliance warnings
    export_warnings = _generate_warnings(items)

    # Build export package
    pkg = ExportPackage(
        export_metadata={
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "disclaimer": (
                "This is a draft review package — not a tax return. "
                "It does not provide final tax advice and does not replace "
                "review by a registered tax agent."
            ),
            "status": "draft",
            "schema_version": "0.1.0",
        },
        session={
            "id": session.id,
            "title": session.title or "Untitled Session",
            "financial_year": session.financial_year,
            "status": session.status,
        },
        summary={
            "total_documents": len(documents),
            "total_items": len(items),
            "income_count": len(income_items),
            "deduction_count": len(deduction_items),
            "needs_review_count": len(needs_review_items),
            "approved_count": len(approved_items),
            "total_income_aud": round(total_income, 2),
            "total_candidate_deductions_aud": round(total_deductions, 2),
        },
        income_items=[_item_to_json(i) for i in income_items],
        deduction_items=[_item_to_json(i) for i in deduction_items],
        needs_review_items=[
            {
                "id": i.id,
                "type": i.item_type,
                "category": i.category,
                "amount": i.amount,
                "description": i.description or "",
                "review_reason": i.review_reason,
            }
            for i in needs_review_items
        ],
        out_of_scope_items=[
            {
                "id": i.id,
                "category": i.category,
                "description": i.description or "",
            }
            for i in out_of_scope_items
        ],
        source_documents=[
            {
                "id": d.id,
                "filename": d.original_filename,
                "mime_type": d.mime_type,
                "size_bytes": d.file_size_bytes,
                "status": d.status,
            }
            for d in documents
        ],
        export_warnings=export_warnings,
    )

    # Write audit
    await write_audit(
        db, "tax_session", session_id, "exported",
        details={
            "total_items": len(items),
            "income_count": len(income_items),
            "deduction_count": len(deduction_items),
            "needs_review_count": len(needs_review_items),
            "warnings_count": len(export_warnings),
        },
    )

    # Persist to export_packages table
    pkg_dict = pkg.to_dict()
    export_record = ExportPackageModel(
        session_id=session_id,
        format="json",
        item_count=len(items),
        total_amount=round(total_deductions, 2) if total_deductions else None,
        total_taxable=None,
        compliance_score=None,
        export_data=json.dumps(pkg_dict),
        exported_by="system",
    )
    db.add(export_record)
    await db.commit()

    return pkg_dict


def _generate_warnings(items: list[TaxItem]) -> list[str]:
    """Generate compliance/risk warnings based on item characteristics."""
    warnings = []

    # Check for high-risk categories
    for item in items:
        if item.category in _ATO_HIGH_RISK_CATEGORIES and item.needs_review:
            hint = _ATO_HIGH_RISK_CATEGORIES[item.category]
            warnings.append(
                f"Item '{item.description or item.category}' needs review. "
                f"{hint}"
            )

    # Check for low-confidence items
    low_conf_items = [i for i in items if i.confidence is not None and i.confidence < 0.7 and not i.needs_review]
    for item in low_conf_items:
        warnings.append(
            f"Item '{item.description or item.category}' has low confidence "
            f"({item.confidence:.0%}) but was auto-approved — verify manually."
        )

    # Check for items with no amount
    no_amount = [i for i in items if i.amount is None and i.item_type in ("income", "deduction")]
    if no_amount:
        warnings.append(
            f"{len(no_amount)} item(s) have no dollar amount recorded."
        )

    # General review notice
    needs_review = [i for i in items if i.needs_review]
    if needs_review:
        warnings.append(
            f"{len(needs_review)} item(s) require human review before use."
        )

    return list(dict.fromkeys(warnings))  # deduplicate
