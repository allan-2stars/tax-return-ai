"""Export package Pydantic schemas."""
from datetime import datetime
from pydantic import BaseModel


class ExportPackageRecord(BaseModel):
    """Lightweight record returned by the export history endpoint."""
    id: str
    session_id: str
    format: str
    item_count: int
    total_amount: float | None
    total_taxable: float | None
    compliance_score: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
