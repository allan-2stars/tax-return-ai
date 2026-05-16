"""TaxItem Pydantic schemas."""
from datetime import datetime
from pydantic import BaseModel, Field


class TaxItemCreate(BaseModel):
    session_id: str
    item_type: str
    category: str
    amount: float | None = None
    description: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    needs_review: bool = True
    review_status: str = "needs_review"
    review_reason: str | None = None
    ato_reference_hint: str | None = None


class TaxItemUpdate(BaseModel):
    item_type: str | None = None
    category: str | None = None
    amount: float | None = None
    description: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    ato_reference_hint: str | None = None


class TaxItemReview(BaseModel):
    """Used when a user reviews/approves an item."""
    needs_review: bool
    review_reason: str | None = None


class BulkReviewRequest(BaseModel):
    """Review multiple items at once."""
    item_ids: list[str]
    needs_review: bool
    review_reason: str | None = None


class TaxItemResponse(BaseModel):
    id: str
    session_id: str
    item_type: str
    category: str
    amount: float | None
    description: str | None
    confidence: float | None
    needs_review: bool
    review_status: str
    review_reason: str | None
    ato_reference_hint: str | None
    reviewed_at: datetime | None
    reviewed_by: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkspaceReviewStatusUpdate(BaseModel):
    review_status: str
    note: str | None = None


class WorkspaceReviewSummaryResponse(BaseModel):
    total_items: int
    draft: int
    needs_review: int
    confirmed: int
    excluded: int
    tax_agent_review: int
    manual_review_documents: int = 0
    ready_for_export: bool
    blocking_reasons: list[str]


class WorkspaceManualItemCreateRequest(BaseModel):
    description: str = Field(min_length=1, max_length=2000)
    item_type: str = "needs_review"
    category: str = "needs_review"
    amount: float | None = None
    review_status: str = "needs_review"
    note: str | None = None
