"""AI provider ABC. All AI calls go through this interface — never import vendor SDKs in services."""
from abc import ABC, abstractmethod
from typing import Any


class AIProvider(ABC):
    @abstractmethod
    async def classify(
        self,
        extracted_text: str,
        document_id: str,
        financial_year: str,
        skill_context: str,
    ) -> dict[str, Any]:
        """
        Classify extracted text. Return a dict matching tax_analysis_output schema v1.1.
        Raise ValueError if response cannot be parsed or fails schema validation.
        """

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the provider is reachable."""
