"""tax-return-ai — FastAPI application entry point."""
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import engine
from app.db.base import Base
from app.db.deps import get_db
from app.routers import audit, jobs, monitoring, auth, workspaces, legacy
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.logging import StructuredLoggingMiddleware
from app.middleware.uuid_validation import UUIDValidationMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup if they don't exist."""
    logging.basicConfig(
        level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
        format="%(message)s",  # JSON — we format manually
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="tax-return-ai",
    description=(
        "Australian individual tax-ready data generator. "
        "This tool organises tax documents and prepares a review package. "
        "It does not provide final tax advice, lodge returns, or replace a registered tax agent."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — explicit origins. No wildcard because allow_credentials=True.
# Cloudflare proxy handles HTTPS termination; backend sees forwarded requests.
_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3010",
    "https://tax.signpega.com",
]
_env_origins = os.getenv("CORS_ORIGINS", "")
if _env_origins:
    _CORS_ORIGINS.extend([o.strip() for o in _env_origins.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security headers
app.add_middleware(SecurityHeadersMiddleware)

# Structured JSON logging (before rate limit so every request gets a request_id)
app.add_middleware(StructuredLoggingMiddleware)

# Rate limiting
app.add_middleware(
    RateLimitMiddleware,
    limits={
        r"^/api/documents/upload": (10, 60),     # 10 uploads per minute
        r"^/api/sessions": (30, 60),             # 30 session list/creates per minute
        r"^/api/": (60, 60),                       # 60 general API calls per minute
    },
)

# UUID validation for path parameters
app.add_middleware(UUIDValidationMiddleware)


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health(db: AsyncSession = Depends(get_db)) -> dict:
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "product": "tax-return-ai",
        "database": "connected" if db_ok else "disconnected",
    }


# ── API Routers ────────────────────────────────────────────────────────────────
app.include_router(audit.router)
app.include_router(jobs.router)
app.include_router(monitoring.router)
app.include_router(auth.router)
app.include_router(workspaces.router)
app.include_router(legacy.router)
