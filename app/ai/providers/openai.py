"""OpenAI AI provider — real classification via OpenAI API.

Uses GPT-4o-mini (or configured model) to produce structured tax analysis JSON
conforming to skills/tax-return-specialist/schemas/tax_analysis_output.schema.json.
Falls back to a basic classification dict if the API response is unparseable.

Keep the openai SDK import inside this file only — never import it in services.
"""

from app.ai.providers.base import AIProvider, ClassificationResult
from app.ai.providers.shared import (
    CLASSIFICATION_SYSTEM_PROMPT,
    _build_classify_prompt,
    build_classification_result,
    parse_json_response,
)
from app.config import settings

# OpenAI JSON Schema for structured output
CLASSIFICATION_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "item_type": {
            "type": "string",
            "enum": ["income", "deduction", "non_claimable", "needs_review", "out_of_scope"],
        },
        "category": {
            "type": "string",
            "enum": [
                "salary_wages", "allowance", "bank_interest", "dividend",
                "government_payment", "other_income", "unknown_income",
                "foreign_income", "business_income", "rental_income",
                "capital_gain", "crypto_gain", "trust_distribution",
                "work_related_car_expense", "work_related_travel_expense",
                "work_related_clothing_laundry", "work_related_self_education",
                "work_from_home", "tools_equipment", "union_fee",
                "professional_membership_fee", "donation", "tax_agent_fee",
                "income_protection", "other_deduction", "unknown_deduction",
                "personal_expense", "private_or_mixed_use", "insufficient_evidence",
                "duplicate_document", "reimbursed_or_potential_double_dip",
                "out_of_scope", "needs_review",
            ],
        },
        "amount": {"type": ["number", "null"]},
        "description": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
        "review_status": {
            "type": "string",
            "enum": [
                "auto_classified", "needs_user_review", "needs_tax_agent_review",
                "user_confirmed", "excluded_by_user", "ready_for_export",
            ],
        },
        "reasoning_summary": {"type": "string"},
        "missing_fields": {"type": "array", "items": {"type": "string"}},
        "suggested_user_questions": {"type": "array", "items": {"type": "string"}},
        "supplier_or_source": {"type": ["string", "null"]},
        "work_use_percentage": {"type": ["number", "null"]},
        "ato_reference_hint": {"type": ["string", "null"]},
        "evidence_status": {
            "type": "string",
            "enum": ["complete", "partial", "missing_or_incomplete"],
        },
        "source_evidence": {
            "type": "object",
            "properties": {
                "page": {"type": ["integer", "null"]},
                "snippet": {"type": ["string", "null"]},
                "ocr_confidence": {"type": ["number", "null"]},
            },
        },
        "audit": {
            "type": "object",
            "properties": {
                "analysis_timestamp": {"type": "string"},
                "analysis_method": {"type": "string", "enum": ["ai", "rules", "manual", "hybrid"]},
                "model_version": {"type": ["string", "null"]},
            },
        },
    },
    "required": [
        "item_type", "category", "description", "confidence",
        "risk_level", "review_status", "reasoning_summary",
    ],
    "additionalProperties": False,
}


class OpenAIProvider(AIProvider):
    def __init__(self):
        self.api_key = settings.openai_api_key
        self.model = settings.ai_model or "gpt-4o-mini"

    async def classify(
        self,
        extracted_text: str,
        document_id: str,
        financial_year: str,
        skill_context: str = "",
    ) -> list[ClassificationResult]:
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.api_key)

            user_prompt = _build_classify_prompt(
                extracted_text, document_id, financial_year, skill_context
            )

            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": CLASSIFICATION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "tax_analysis_output",
                        "strict": True,
                        "schema": CLASSIFICATION_RESPONSE_SCHEMA,
                    },
                },
                max_tokens=4096,
            )

            raw = response.choices[0].message.content or ""

            parsed = parse_json_response(raw)
            if parsed:
                return [build_classification_result(
                    parsed,
                    document_id,
                    financial_year,
                    provider_name="openai",
                    default_description="Classified by OpenAI.",
                )]

            # Fallback
            return [ClassificationResult({
                "document_id": document_id,
                "financial_year": financial_year,
                "item_type": "needs_review",
                "category": "needs_review",
                "amount": None,
                "currency": "AUD",
                "description": "OpenAI response could not be parsed.",
                "confidence": 0.1,
                "needs_review": True,
                "review_reason": f"Failed to parse response. Raw: {raw[:200]}...",
                "ato_reference_hint": None,
                "metadata": {
                    "provider": "openai",
                    "model_version": self.model,
                    "raw_response_preview": raw[:500],
                },
            })]

        except Exception as e:
            return [ClassificationResult({
                "document_id": document_id,
                "financial_year": financial_year,
                "item_type": "needs_review",
                "category": "needs_review",
                "amount": None,
                "currency": "AUD",
                "description": f"OpenAI API error: {e}",
                "confidence": 0.0,
                "needs_review": True,
                "review_reason": f"API call failed: {e}",
                "ato_reference_hint": None,
                "metadata": {
                    "provider": "openai",
                    "error": str(e),
                },
            })]

    async def health_check(self) -> bool:
        """Check if the OpenAI API is reachable."""
        if not self.api_key:
            return False
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.api_key)
            await client.models.list(limit=1)
            return True
        except Exception:
            return False
