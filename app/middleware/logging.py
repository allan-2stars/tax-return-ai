"""Structured JSON logging middleware — adds request_id, logs all requests."""
import uuid
import logging
import time
import json
from collections.abc import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Logs all requests as JSON with timing, request_id, status."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.logger = logging.getLogger("tax-return-ai.http")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        start = time.time()
        response = await call_next(request)
        elapsed_ms = round((time.time() - start) * 1000)

        self.logger.info(json.dumps({
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "elapsed_ms": elapsed_ms,
            "client_ip": request.client.host if request.client else "unknown",
        }))

        response.headers["X-Request-ID"] = request_id
        return response
