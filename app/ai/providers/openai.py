"""OpenAI provider stub. Implements AIProvider ABC."""
from typing import Any
from app.ai.providers.base import AIProvider


class OpenAIProvider(AIProvider):
    async def classify(self, extracted_text: str, document_id: str,
                       financial_year: str, skill_context: str) -> dict[str, Any]:
        raise NotImplementedError("OpenAIProvider.classify not yet implemented")

    async def health_check(self) -> bool:
        raise NotImplementedError
