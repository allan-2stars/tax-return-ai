"""Classification Pydantic schemas."""
from pydantic import BaseModel


class ClassificationRequest(BaseModel):
    """Request to classify a document."""
    document_id: str
    session_id: str
    extracted_text: str
    financial_year: str | None = None
    skill_context: str = ""


class ClassificationResponse(BaseModel):
    """Response from a classification run."""
    item_id: str
    document_id: str
    session_id: str
    item_type: str
    category: str
    amount: float | None
    description: str | None
    confidence: float | None
    needs_review: bool
    review_reason: str | None
    ato_reference_hint: str | None
