"""AI provider ABC. All AI calls go through this interface — never import vendor SDKs in services."""
from abc import ABC, abstractmethod
from typing import Any


class ClassificationResult(dict):
    """Typed dict-like result from an AI classification.

    Fields:
      item_type: income | deduction | offset | needs_review | out_of_scope
      category: str — e.g. salary_wages, tools_equipment, work_from_home
      amount: float | None — extracted dollar amount
      confidence: float 0-1 — how confident the AI is
      needs_review: bool — true if uncertain, low confidence, or missing data
      review_reason: str | None — explanation of why review is needed
      ato_reference_hint: str | None — optional ATO category ref (e.g. D1, D5)
    """
    pass


class AIProvider(ABC):
    @abstractmethod
    async def classify(
        self,
        extracted_text: str,
        document_id: str,
        financial_year: str,
        skill_context: str,
    ) -> list[ClassificationResult]:
        """
        Classify extracted text from a document.

        Returns a list of classification results — one per detected item/line
        in the document. Each dict has at minimum:
          item_type, category, confidence, needs_review

        If confidence is low (< 0.7) or tax rule is uncertain:
          needs_review must be True.

        Raises ValueError if response cannot be parsed.
        """

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the provider is reachable."""
