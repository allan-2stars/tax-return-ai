from pydantic import BaseModel, Field


class SetupStatusResponse(BaseModel):
    is_configured: bool
    auth_mode: str = "local"
    has_active_user: bool


class SetupRequest(BaseModel):
    master_password: str = Field(min_length=8)
    display_name: str | None = None
    email: str | None = None


class UnlockRequest(BaseModel):
    master_password: str


class SessionResponse(BaseModel):
    is_authenticated: bool
    app_state: str
    user_id: str | None = None
    display_name: str | None = None
    expires_at: str | None = None


class SetupResponse(BaseModel):
    recovery_key: str
    app_state: str
    session_token: str | None = None
