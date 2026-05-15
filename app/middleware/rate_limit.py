"""Simple in-memory rate limiter — no external dependencies."""
import time
from collections import defaultdict
from collections.abc import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-memory sliding-window rate limiter.

    Usage in main.py:
        app.add_middleware(RateLimitMiddleware, limits={
            r"^/api/documents/upload": (10, 60),    # 10 uploads per 60s
            r"^/api/sessions": (30, 60),             # 30 session reads per 60s
            r"^/api/": (60, 60),                      # 60 general API calls per 60s
        })
    """

    def __init__(self, app: ASGIApp, limits: dict[str, tuple[int, int]] | None = None):
        super().__init__(app)
        self.limits = limits or {}
        # {path_pattern: [(timestamp, ip), ...]}
        self._requests: dict[str, list[tuple[float, str]]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks
        if request.url.path == "/api/health":
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        if client_ip == "unknown":
            return await call_next(request)

        import re

        for pattern, (max_requests, window_seconds) in self.limits.items():
            if re.match(pattern, request.url.path):
                now = time.time()
                window_start = now - window_seconds
                key = f"{pattern}:{client_ip}"

                # Clean old entries
                self._requests[key] = [
                    (ts, ip) for ts, ip in self._requests[key] if ts > window_start
                ]

                if len(self._requests[key]) >= max_requests:
                    oldest = self._requests[key][0][0]
                    return JSONResponse(
                        status_code=429,
                        content={
                            "detail": "Rate limit exceeded. Try again later.",
                            "retry_after_seconds": int(
                                window_seconds - (now - oldest)
                            ),
                        },
                    )

                self._requests[key].append((now, client_ip))
                break

        return await call_next(request)
