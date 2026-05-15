"""Router registry — import and include all API routers."""
from app.routers import sessions, documents, items, audit

__all__ = ["sessions", "documents", "items", "audit"]
