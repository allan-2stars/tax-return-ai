"""AppSetting Pydantic schemas."""
from datetime import datetime
from pydantic import BaseModel


class AppSettingCreate(BaseModel):
    key: str
    value: str | None = None
    description: str | None = None


class AppSettingResponse(BaseModel):
    key: str
    value: str | None
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
