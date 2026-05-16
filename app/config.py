"""
Application configuration — all env vars loaded here.
Access via: from app.config import settings
"""
from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Edition
    edition: str = "personal"               # personal | pro | team
    financial_year: str = "2025-2026"       # default for new sessions

    # AI
    ai_provider: str = "mock"          # anthropic | openai | deepseek | mock
    ai_model: str | None = None
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"

    # OCR
    ocr_provider: str = "pdfplumber"        # pdfplumber | tesseract | mock

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/taxapp.db"

    # Storage
    storage_backend: str = "local"          # local | s3
    storage_local_path: str = "./data/uploads"
    aws_bucket: str = ""
    aws_region: str = "ap-southeast-2"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

    # App
    max_upload_size_mb: int = 20
    log_level: str = "INFO"
    redact_sensitive_logs: bool = True
    telemetry_enabled: bool = False
    processing_timeout_seconds: int = 300              # max pipeline run time (5 min)
    enable_legacy_export_routes: bool = False
    cookie_secure: bool = True
    cookie_samesite: str = "lax"  # lax | strict | none
    cookie_domain: str | None = None
    allow_insecure_cookie_local_dev: bool = False
    session_idle_timeout_minutes: int = 30
    session_absolute_timeout_hours: int = 12
    session_idle_timeout_seconds: int | None = None
    session_absolute_timeout_seconds: int | None = None
    lock_on_browser_close: bool = False

    @field_validator("ai_provider")
    @classmethod
    def validate_ai_provider(cls, value: str) -> str:
        normalized = (value or "").strip().lower()
        allowed = {"anthropic", "openai", "deepseek", "mock"}
        if normalized not in allowed:
            raise ValueError(
                "AI classification is not configured correctly. Set AI_PROVIDER to anthropic, openai, deepseek, or mock."
            )
        return normalized

    # ── Feature flags — always use these, never inline os.getenv("EDITION") ──

    @property
    def batch_processing_enabled(self) -> bool:
        return self.edition in ("pro", "team")

    @property
    def auth_required(self) -> bool:
        return self.edition == "team"

    @property
    def handoff_export_enabled(self) -> bool:
        return self.edition in ("pro", "team")

    @property
    def s3_storage(self) -> bool:
        return self.storage_backend == "s3"

    @property
    def postgres_db(self) -> bool:
        return self.database_url.startswith("postgresql")

    @property
    def effective_session_idle_timeout_seconds(self) -> int:
        if self.session_idle_timeout_seconds is not None:
            return max(60, int(self.session_idle_timeout_seconds))
        return max(60, int(self.session_idle_timeout_minutes) * 60)

    @property
    def effective_session_absolute_timeout_seconds(self) -> int:
        if self.session_absolute_timeout_seconds is not None:
            return max(300, int(self.session_absolute_timeout_seconds))
        return max(300, int(self.session_absolute_timeout_hours) * 3600)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
