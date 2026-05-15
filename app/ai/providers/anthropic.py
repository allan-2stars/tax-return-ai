"""Anthropic AI provider — real classification via Anthropic API.

Uses Claude to produce structured tax analysis JSON conforming to
skills/tax-return-specialist/schemas/tax_analysis_output.schema.json.
Falls back to a basic classification dict if the API response is unparseable.

Keep the anthropic SDK import inside this file only — never import it in services.
"""

from app.ai.providers.base import AIProvider, ClassificationResult
from app.ai.providers.shared import (
    CLASSIFICATION_SYSTEM_PROMPT,
    _build_classify_prompt,
    build_classification_result,
    parse_json_response,
)
from app.config import settings


class AnthropicProvider(AIProvider):
    def __init__(self):
        self.api_key = settings.anthropic_api_key
        self.model = settings.ai_model or "claude-3-haiku-20240307"

    async def classify(
        self,
        extracted_text: str,
        document_id: str,
        financial_year: str,
        skill_context: str = "",
    ) -> list[ClassificationResult]:
        try:
            import anthropic

            client = anthropic.AsyncAnthropic(api_key=self.api_key)

            user_prompt = _build_classify_prompt(
                extracted_text, document_id, financial_year, skill_context
            )

            response = await client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=CLASSIFICATION_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )

            raw = response.content[0].text if response.content else ""

            parsed = parse_json_response(raw)
            if parsed:
                return [build_classification_result(
                    parsed,
                    document_id,
                    financial_year,
                    provider_name="anthropic",
                    default_description="Classified by Anthropic.",
                )]

            # Fallback: minimal result
            return [ClassificationResult({
                "document_id": document_id,
                "financial_year": financial_year,
                "item_type": "needs_review",
                "category": "needs_review",
                "amount": None,
                "currency": "AUD",
                "description": "Anthropic response could not be parsed.",
                "confidence": 0.1,
                "needs_review": True,
                "review_reason": f"Failed to parse Claude response. Raw: {raw[:200]}...",
                "ato_reference_hint": None,
                "metadata": {
                    "provider": "anthropic",
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
                "description": f"Anthropic API error: {e}",
                "confidence": 0.0,
                "needs_review": True,
                "review_reason": f"API call failed: {e}",
                "ato_reference_hint": None,
                "metadata": {
                    "provider": "anthropic",
                    "error": str(e),
                },
            })]

    async def health_check(self) -> bool:
        """Check if the Anthropic API is reachable."""
        if not self.api_key:
            return False
        try:
            import anthropic

            client = anthropic.AsyncAnthropic(api_key=self.api_key)
            await client.models.list(limit=1)
            return True
        except Exception:
            return False
