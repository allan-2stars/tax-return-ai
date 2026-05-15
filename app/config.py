"""
Application configuration — all env vars loaded here.
Access via: from app.config import settings
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Edition
    edition: str = "personal"               # personal | pro | team
    financial_year: str = "2025-2026"       # default for new sessions

    # AI
    ai_provider: str = "mock"          # anthropic | openai | mock
    ai_model: str | None = None
    anthropic_api_key: str = ""
    openai_api_key: str = ""

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


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
