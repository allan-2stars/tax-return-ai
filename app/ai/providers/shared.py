"""Shared utilities for AI providers — JSON parsing, prompt building, result mapping.

Keeps the DRY logic used by both anthropic.py and openai.py in one place.
"""

import json
import re
from datetime import UTC, datetime
from typing import Any

from app.ai.providers.base import ClassificationResult

# ── System Prompt ───────────────────────────────────────────────────────────

CLASSIFICATION_SYSTEM_PROMPT = """You are a specialised Australian tax document analyst. Your role is to classify
individual tax documents into structured tax items for the ATO financial year.

Rules:
1. Classify items as: income, deduction, non_claimable, needs_review, or out_of_scope.
2. Categories must be one of the ATO-aligned enum values (salary_wages, tools_equipment, etc.).
3. Set confidence as a float 0-1 — be conservative for ambiguous documents.
4. If confidence < 0.7, set needs_review=true and explain why.
5. Set risk_level: low, medium, or high based on tax audit risk.
6. Never assume work-use percentage or private-use split unless the document explicitly states it.
7. If a deduction looks like it could be private or reimbursed, flag it as needs_review.
8. For BAS/GST/ABN mentions, classify as out_of_scope with needs_review=true.
9. All amounts are in AUD.
10. Financial year runs 1 July – 30 June.

Return ONLY valid JSON matching the TaxAnalysisOutput schema.
No preamble, no markdown, no explanation — just the JSON object."""


# ── Prompt Builder ──────────────────────────────────────────────────────────

def _build_classify_prompt(
    extracted_text: str,
    document_id: str,
    financial_year: str,
    skill_context: str,
) -> str:
    """Build the user message for the classify call."""
    parts = [f"Classify this document text for FY {financial_year}:\n"]
    if skill_context:
        parts.append(f"Additional context: {skill_context}\n")
    parts.append(f"Document ID: {document_id}\n")
    parts.append(f"--- BEGIN DOCUMENT TEXT ---\n{extracted_text}\n--- END DOCUMENT TEXT ---")
    return "\n".join(parts)


# ── JSON Response Parsing (3 fallback strategies) ───────────────────────────

def parse_json_response(raw: str) -> dict[str, Any] | None:
    """Try to extract a valid JSON object from an AI response.

    Strategy 1: Direct json.loads on stripped text.
    Strategy 2: Extract from ```json ... ``` or ``` ... ``` fence.
    Strategy 3: Find the first { ... } block with balanced braces.
    """
    text = raw.strip()

    # Strategy 1: Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract from markdown code fence
    m = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Strategy 3: First { ... } block with balanced braces
    brace_start = text.find("{")
    if brace_start >= 0:
        depth = 0
        for i in range(brace_start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[brace_start : i + 1])
                    except json.JSONDecodeError:
                        break
    return None


# ── ATO Reference Mapping ──────────────────────────────────────────────────

_ATO_REF_MAP: dict[str, str] = {
    "salary_wages": "Salary/Wages",
    "work_related_car_expense": "D1",
    "work_related_travel_expense": "D2",
    "work_related_clothing_laundry": "D3",
    "work_related_self_education": "D4",
    "work_from_home": "D5",
    "tools_equipment": "D5",
    "union_fee": "D5",
    "professional_membership_fee": "D5",
    "donation": "D5",
    "tax_agent_fee": "D5",
    "income_protection": "D5",
    "bank_interest": "Interest",
    "dividend": "Dividend",
    "government_payment": "Government Payment",
    "foreign_income": "Foreign Income",
    "business_income": "Business Income",
}


def _infer_ato_reference(category: str) -> str | None:
    """Infer a basic ATO label reference from category."""
    return _ATO_REF_MAP.get(category)


# ── ClassificationResult Builder ────────────────────────────────────────────

def build_classification_result(
    parsed: dict[str, Any],
    document_id: str,
    financial_year: str,
    *,
    provider_name: str = "unknown",
    default_description: str = "Classified by AI.",
) -> ClassificationResult:
    """Map the full TaxAnalysisOutput schema to our compact ClassificationResult."""
    item_type = parsed.get("item_type", "needs_review")
    category = parsed.get("category", "needs_review")
    confidence = float(parsed.get("confidence", 0.5))
    review_status = parsed.get("review_status", "needs_user_review")
    needs_review = review_status not in ("auto_classified", "user_confirmed", "ready_for_export")
    reasoning = parsed.get("reasoning_summary", "")
    missing = parsed.get("missing_fields", [])
    questions = parsed.get("suggested_user_questions", [])

    # Build a readable review reason
    review_reason: str | None = None
    if needs_review:
        parts = []
        if reasoning:
            parts.append(reasoning)
        if missing:
            parts.append(f"Missing fields: {', '.join(missing)}")
        if questions:
            parts.append(f"Suggested: {'; '.join(questions)}")
        review_reason = " | ".join(parts) if parts else "Requires human review."

    # Map risk level
    risk = parsed.get("risk_level", "medium")

    # ATO reference hint
    ato_hint = parsed.get("ato_reference_hint") or _infer_ato_reference(category)

    audit_info = parsed.get("audit", {})
    source_evidence = parsed.get("source_evidence", {})

    return ClassificationResult({
        "document_id": document_id,
        "financial_year": financial_year,
        "item_type": item_type,
        "category": category,
        "amount": parsed.get("amount"),
        "currency": "AUD",
        "description": parsed.get("description", default_description),
        "confidence": confidence,
        "needs_review": needs_review,
        "review_reason": review_reason,
        "ato_reference_hint": ato_hint,
        "risk_level": risk,
        "reasoning_summary": reasoning,
        "evidence_status": parsed.get("evidence_status", "partial"),
        "supplier_or_source": parsed.get("supplier_or_source"),
        "work_use_percentage": parsed.get("work_use_percentage"),
        "missing_fields": missing,
        "suggested_user_questions": questions,
        "source_evidence": source_evidence,
        "metadata": {
            "provider": provider_name,
            "analysis_timestamp": audit_info.get("analysis_timestamp", datetime.now(UTC).isoformat()),
            "model_version": audit_info.get("model_version", provider_name),
            "analysis_method": audit_info.get("analysis_method", "ai"),
        },
    })
