"""Mock AI provider for tests. Returns deterministic classification output."""
import uuid
from datetime import UTC, datetime
from typing import Any
from app.ai.providers.base import AIProvider, ClassificationResult


class MockProvider(AIProvider):
    async def classify(
        self,
        extracted_text: str,
        document_id: str,
        financial_year: str,
        skill_context: str,
    ) -> list[ClassificationResult]:
        """Return deterministic mock classification.

        Returns a list of classification results — one per detected item/line
        in the document. Multiple keywords in the text produce multiple results.
        The mock sets needs_review=True when confidence would be low
        (< 0.7) or when text contains certain trigger keywords.
        """
        text_lower = extracted_text.lower()

        # Trigger keywords that indicate needs_review
        has_trigger = any(kw in text_lower for kw in [
            "maybe", "possibly", "unsure", "blurry", "unclear",
            "reimbursed", "private", "mixed", "duplicate",
        ])

        results: list[ClassificationResult] = []
        matched_any = False

        def _make_base() -> ClassificationResult:
            """Create a new base result dict for each item."""
            return {
                "document_id": document_id,
                "financial_year": financial_year,
                "item_type": "needs_review",
                "category": "needs_review",
                "amount": None,
                "currency": "AUD",
                "description": f"Mock classification of: {extracted_text[:100]}...",
                "confidence": 0.5,
                "needs_review": True,
                "review_reason": "Mock provider — no real classification performed. Needs human review.",
                "ato_reference_hint": None,
                "metadata": {
                    "provider": "mock",
                    "analysis_timestamp": datetime.now(UTC).isoformat(),
                    "model_version": "mock-0.1",
                },
            }

        def _apply_trigger(result: ClassificationResult) -> ClassificationResult:
            """Override needs_review if trigger words found."""
            if has_trigger and result.get("confidence", 0.0) >= 0.7:
                result["needs_review"] = True
                result["review_reason"] = (
                    result.get("review_reason")
                    or "Trigger terms detected — needs user confirmation."
                )
            return result

        # Check for each keyword match independently
        if "salary" in text_lower or "wages" in text_lower or "income" in text_lower:
            matched_any = True
            r = _make_base()
            r.update({
                "item_type": "income",
                "category": "salary_wages",
                "confidence": 0.95,
                "needs_review": has_trigger,
                "review_reason": None if not has_trigger else "Review suggested due to uncertain terms in document.",
            })
            results.append(_apply_trigger(r))

        if "officeworks" in text_lower or "tools" in text_lower or "equipment" in text_lower:
            matched_any = True
            r = _make_base()
            r.update({
                "item_type": "deduction",
                "category": "tools_equipment",
                "confidence": 0.70,
                "needs_review": True,
                "review_reason": "Work-use percentage not confirmed in document.",
                "ato_reference_hint": "D5",
            })
            results.append(_apply_trigger(r))

        if "electricity" in text_lower or "wfh" in text_lower or "home office" in text_lower:
            matched_any = True
            r = _make_base()
            r.update({
                "item_type": "deduction",
                "category": "work_from_home",
                "confidence": 0.65,
                "needs_review": True,
                "review_reason": "Work-use percentage and reimbursement status not confirmed.",
                "ato_reference_hint": "D5",
            })
            results.append(_apply_trigger(r))

        if "bas" in text_lower or "gst" in text_lower or "abn" in text_lower:
            matched_any = True
            r = _make_base()
            r.update({
                "item_type": "out_of_scope",
                "category": "out_of_scope",
                "confidence": 0.85,
                "needs_review": True,
                "review_reason": "BAS/GST language detected. May indicate business or sole trader activity requiring registered tax agent review.",
                "ato_reference_hint": None,
            })
            results.append(_apply_trigger(r))

        if "donation" in text_lower or "charity" in text_lower or "gift" in text_lower:
            matched_any = True
            r = _make_base()
            r.update({
                "item_type": "deduction",
                "category": "donation",
                "confidence": 0.80,
                "needs_review": False,
                "review_reason": None,
                "ato_reference_hint": "D5",
            })
            results.append(_apply_trigger(r))

        if "union" in text_lower or "membership" in text_lower:
            matched_any = True
            r = _make_base()
            r.update({
                "item_type": "deduction",
                "category": "union_fee",
                "confidence": 0.90,
                "needs_review": False,
                "review_reason": None,
                "ato_reference_hint": "D5",
            })
            results.append(_apply_trigger(r))

        # If no keywords matched but text is non-empty, return a needs_review item
        if not matched_any and extracted_text.strip():
            r = _make_base()
            r.update({
                "item_type": "needs_review",
                "category": "needs_review",
            })
            results.append(_apply_trigger(r))

        # If text is empty, return a single needs_review item with low confidence
        if not extracted_text.strip():
            r = _make_base()
            r.update({
                "item_type": "needs_review",
                "category": "insufficient_evidence",
                "confidence": 0.1,
                "needs_review": True,
                "review_reason": "No extracted text to classify.",
            })
            results = [r]

        return results

    async def health_check(self) -> bool:
        return True
