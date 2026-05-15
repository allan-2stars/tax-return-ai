"""Mock AI provider for tests. Returns deterministic valid schema output."""
import uuid
from datetime import UTC, datetime
from typing import Any
from app.ai.providers.base import AIProvider


class MockProvider(AIProvider):
    async def classify(self, extracted_text: str, document_id: str,
                       financial_year: str, skill_context: str) -> dict[str, Any]:
        return {
            "schema_version": "1.1",
            "financial_year": financial_year,
            "document_id": document_id,
            "item_id": str(uuid.uuid4()),
            "item_type": "needs_review",
            "category": "needs_review",
            "amount": None,
            "work_use_percentage": None,
            "currency": "AUD",
            "date": None,
            "date_in_financial_year": None,
            "supplier_or_source": None,
            "abn": None,
            "description": "Mock classification — replace with real provider for production.",
            "confidence": 0.5,
            "evidence_status": "missing_or_incomplete",
            "risk_level": "medium",
            "review_status": "needs_user_review",
            "reasoning_summary": "Mock provider — no real classification performed.",
            "alternative_interpretations": [],
            "missing_fields": ["amount", "date", "supplier_or_source"],
            "suggested_user_questions": ["What type of document is this?"],
            "source_evidence": {
                "original_filename": None,
                "file_hash": None,
                "page": None,
                "snippet": extracted_text[:200] if extracted_text else None,
                "bounding_box": None,
                "ocr_confidence": None,
            },
            "audit": {
                "analysis_timestamp": datetime.now(UTC).isoformat(),
                "analysis_method": "ai",
                "user_confirmed": False,
                "user_confirmed_at": None,
                "model_version": "mock-0.1",
                "skill_version": "1.1",
                "correction_history": [],
            },
        }

    async def health_check(self) -> bool:
        return True
