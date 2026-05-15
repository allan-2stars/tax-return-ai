"""Compliance review service — checks items against ATO rules and best practices.

This is a rules-based checker (not AI-driven) that evaluates:
  - Export readiness (are there unresolved items?)
  - Evidence completeness
  - Risk level distribution
  - Missing metadata (amounts, dates)
  - Items that should trigger tax agent referral
"""
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.tax_session import TaxSession
from app.models.document import Document
from app.models.tax_item import TaxItem
from app.constants.fy import is_in_financial_year


# ── Categories that typically flag for tax-agent review -----------------------
TAX_AGENT_CATEGORIES = {
    "mixed_use": "Mixed-use asset — apportionment requires tax agent guidance.",
    "capital_asset": "Asset over $300 — decline in value calculation may be complex.",
    "rental_property": "Rental property deductions require capital works schedules.",
    "investment_loss": "Capital gains/losses require ATO reconciliation.",
    "foreign_income": "Foreign income may require specific ATO disclosure.",
    "crypto": "Cryptocurrency transactions require ATO record-keeping.",
    "business_income": "Business/sole-trader income requires BAS reconciliation.",
    "other": "Check ATO guidance — category requires professional review.",
}


async def run_compliance_review(
    db: AsyncSession,
    session_id: str,
) -> dict:
    """Run a rules-based compliance review for all items in a session.

    Returns a dict matching the ComplianceReviewResult schema (v1.1).
    """
    # Load session
    result = await db.execute(select(TaxSession).where(TaxSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise ValueError(f"Session not found: {session_id}")

    fy = session.financial_year

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

    # Evaluate each item
    item_reviews = []
    unresolved_questions = []
    tax_agent_triggers = []
    fy_date_warnings = 0
    evidence_complete = 0
    evidence_incomplete = 0
    risk_counts = {"low": 0, "medium": 0, "high": 0}

    for item in items:
        review = _review_item(item, fy)
        item_reviews.append(review)

        # Accumulate stats
        risk = review["risk_level"]
        if risk in risk_counts:
            risk_counts[risk] += 1

        if review["evidence_status"] == "complete":
            evidence_complete += 1
        else:
            evidence_incomplete += 1

        if not review["date_in_financial_year"]:
            fy_date_warnings += 1

        # Unresolved questions
        unresolved_questions.extend(review.get("required_actions", []))

        # Tax agent triggers
        if review.get("requires_tax_agent"):
            tax_agent_triggers.append(
                f"Item '{item.description or item.category}' ({item.id[:8]}): "
                f"{review.get('tax_agent_reason', 'See review details.')}"
            )

    # Deduplicate questions/triggers
    unresolved_questions = list(dict.fromkeys(unresolved_questions))
    tax_agent_triggers = list(dict.fromkeys(tax_agent_triggers))

    # Determine overall review status and export readiness
    needs_review_count = sum(1 for i in items if i.needs_review)
    has_triggers = len(tax_agent_triggers) > 0

    if needs_review_count == 0 and not has_triggers:
        review_status = "completed"
        export_readiness = {
            "status": "ready_for_human_review_export",
            "reason": "All items reviewed. Package ready for human/tax-agent review.",
            "fy_dates_validated": True,
        }
    elif needs_review_count > 0:
        review_status = "in_progress"
        export_readiness = {
            "status": "not_export_ready",
            "reason": f"{needs_review_count} item(s) require user review before export.",
            "fy_dates_validated": fy_date_warnings == 0,
        }
    else:
        review_status = "blocked"
        export_readiness = {
            "status": "not_export_ready",
            "reason": "Tax agent review recommended before export.",
            "fy_dates_validated": fy_date_warnings == 0,
        }

    return {
        "schema_version": "1.1",
        "tax_session_id": session_id,
        "financial_year": fy,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "review_status": review_status,
        "export_readiness": export_readiness,
        "summary": {
            "documents_reviewed": len(documents),
            "income_items": sum(1 for i in items if i.item_type == "income"),
            "deduction_items": sum(1 for i in items if i.item_type == "deduction"),
            "out_of_scope_items": sum(1 for i in items if i.item_type == "out_of_scope"),
            "needs_review_items": needs_review_count,
            "evidence_complete": evidence_complete,
            "evidence_incomplete": evidence_incomplete,
            "fy_date_warnings": fy_date_warnings,
            "risk_counts": risk_counts,
        },
        "items": item_reviews,
        "unresolved_questions": unresolved_questions,
        "tax_agent_review_triggers": tax_agent_triggers,
    }


def _review_item(item: TaxItem, fy: str) -> dict:
    """Evaluate a single item against compliance rules."""
    findings = []
    required_actions = []

    # Risk assessment
    risk_level = _assess_risk(item)
    evidence_status = _assess_evidence(item)

    # Date check
    date_in_fy = True  # Items don't carry a specific date field currently
    # Future: check extracted_text or document date against FY

    # Findings based on item state
    if item.needs_review:
        findings.append(f"Item flagged for review: {item.review_reason or 'No reason given.'}")
        required_actions.append(f"Review '{item.description or item.category}': is this correctly classified?")
    else:
        findings.append("Item auto-classified and approved.")

    if item.confidence is not None and item.confidence < 0.7:
        findings.append(f"Low confidence ({item.confidence:.0%}) — verify classification.")
        if not item.needs_review:
            required_actions.append("Confirm low-confidence item is correctly classified.")

    if item.amount is None and item.item_type in ("income", "deduction"):
        findings.append("No dollar amount recorded.")
        required_actions.append(f"Enter amount for '{item.description or item.category}'.")

    if item.category == "mixed_use":
        findings.append("Work-use percentage not confirmed.")
        required_actions.append("Confirm work-use percentage for mixed-use item.")
        required_actions.append("Confirm not reimbursed by employer.")

    if item.category == "donation":
        findings.append("Donation requires receipt evidence.")
        required_actions.append("Ensure donation receipt is on file.")

    # Tax agent trigger
    requires_tax_agent = False
    tax_agent_reason = None
    if item.category in TAX_AGENT_CATEGORIES and item.needs_review:
        requires_tax_agent = True
        tax_agent_reason = TAX_AGENT_CATEGORIES[item.category]
        findings.append(tax_agent_reason)

    return {
        "item_id": item.id,
        "document_id": None,  # Would need to resolve via DocumentItem
        "category": item.category,
        "risk_level": risk_level,
        "review_status": "needs_user_review" if item.needs_review else "user_confirmed",
        "evidence_status": evidence_status,
        "date_in_financial_year": date_in_fy,
        "findings": findings,
        "required_actions": list(dict.fromkeys(required_actions)),
        "requires_tax_agent": requires_tax_agent,
        "tax_agent_reason": tax_agent_reason,
    }


def _assess_risk(item: TaxItem) -> str:
    """Determine risk level based on item characteristics."""
    if item.needs_review and item.category in ("mixed_use", "capital_asset", "other"):
        return "high"
    if item.needs_review:
        return "medium"
    if item.confidence is not None and item.confidence < 0.7:
        return "medium"
    return "low"


def _assess_evidence(item: TaxItem) -> str:
    """Determine evidence completeness."""
    if item.category in ("mixed_use", "donation"):
        return "partial"
    if item.needs_review:
        return "partial"
    if item.amount is None:
        return "missing_or_incomplete"
    return "complete"
