"""AuditLog Pydantic schemas."""
from datetime import datetime
from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    action: str
    changed_by: str | None
    details: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
