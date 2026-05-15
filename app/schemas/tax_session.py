"""TaxSession Pydantic schemas."""
from datetime import datetime
from pydantic import BaseModel, Field


class TaxSessionCreate(BaseModel):
    title: str | None = None
    financial_year: str = Field(default="2025-2026", pattern=r"^\d{4}-\d{4}$")
    notes: str | None = None


class TaxSessionUpdate(BaseModel):
    title: str | None = None
    financial_year: str | None = Field(default=None, pattern=r"^\d{4}-\d{4}$")
    status: str | None = None
    notes: str | None = None


class TaxSessionResponse(BaseModel):
    id: str
    title: str | None
    financial_year: str
    status: str
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
