from pydantic import BaseModel, Field


class WorkspaceCreateRequest(BaseModel):
    tax_year: str = Field(min_length=4, max_length=20)
    label: str = Field(min_length=1, max_length=255)


class WorkspaceResponse(BaseModel):
    id: str
    user_id: str
    tax_year: str
    label: str
    status: str
    created_at: str
    updated_at: str
    last_opened_at: str | None
