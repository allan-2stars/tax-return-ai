"""Anthropic AI provider. Implements AIProvider ABC."""
# TODO: implement using anthropic SDK — keep SDK import inside this file only
from typing import Any
from app.ai.providers.base import AIProvider


class AnthropicProvider(AIProvider):
    async def classify(self, extracted_text: str, document_id: str,
                       financial_year: str, skill_context: str) -> dict[str, Any]:
        # TODO: call Anthropic API here, parse JSON, validate against schema
        raise NotImplementedError("AnthropicProvider.classify not yet implemented")

    async def health_check(self) -> bool:
        # TODO: ping API
        raise NotImplementedError
