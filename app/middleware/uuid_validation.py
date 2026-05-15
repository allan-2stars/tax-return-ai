"""Middleware to validate UUID format for path parameters with entity_id patterns."""
import re
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# Matches URL path segments that look like entity IDs in path params
# e.g., /api/sessions/{id}, /api/documents/{id}/pages
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

# Paths that should be skipped (no UUID validation)
SKIP_PREFIXES = (
    "/api/health",
    "/api/sessions?",
    "/api/documents?",
    "/api/items?",
    "/api/audit",
    "/api/monitoring",
)

# Entity path patterns: parts that look like they should be UUIDs
# Any path segment matching this pattern is a potential ID
ENTITY_SEGMENT_PATTERN = re.compile(
    r"^/(?:api/[a-z-]+)/([^/]+)(?:/|$)"
)


class UUIDValidationMiddleware(BaseHTTPMiddleware):
    """Validates that path parameters matching UUID pattern are valid UUIDs.

    Catches malformed UUIDs early with a 400 response instead of letting
    them fall through to a generic 404 from the database query.
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Skip non-API paths and health checks
        if not path.startswith("/api/") or path.startswith(SKIP_PREFIXES):
            return await call_next(request)

        # Extract potential entity IDs from path segments
        parts = path.strip("/").split("/")
        for i, part in enumerate(parts):
            # Skip non-ID segments (api, sessions, documents, etc.)
            if part in {
                "api", "sessions", "documents", "items", "jobs",
                "export", "compliance", "audit", "monitoring",
                "upload", "batch", "status", "pages", "history",
                "stats", "review", "classify", "bulk-review",
                "summary",
            }:
                continue
            # Skip numeric values (offsets, limits)
            if part.isdigit():
                continue
            # Skip query-string-like segments
            if "=" in part or "?" in part:
                continue
            # If it looks like it could be a UUID (has hyphens, right length), validate it
            if "-" in part and len(part) in (36, 38):
                # Strip any trailing slash or query params
                clean = part.split("?")[0].split("/")[0]
                if not UUID_PATTERN.match(clean):
                    return JSONResponse(
                        status_code=400,
                        content={
                            "detail": f"Invalid ID format: '{clean}'. "
                                     f"Expected a valid UUID."
                        },
                    )

        return await call_next(request)
