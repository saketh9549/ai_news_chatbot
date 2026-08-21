"""Simple in-memory rate limiter middleware with localhost exemption."""

import time
from collections import defaultdict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = 300):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window = 60.0
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _get_client_id(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _is_rate_limited(self, client_id: str) -> bool:
        # Exempt local development traffic from rate limiting
        if client_id in ("127.0.0.1", "localhost", "::1", "testclient"):
            return False

        now = time.time()
        window_start = now - self.window

        # Prune old entries
        self._requests[client_id] = [
            t for t in self._requests[client_id] if t > window_start
        ]

        if len(self._requests[client_id]) >= self.requests_per_minute:
            return True

        self._requests[client_id].append(now)
        return False

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for OPTIONS preflight, health checks, and static assets
        if request.method == "OPTIONS" or request.url.path in ("/health", "/docs", "/openapi.json"):
            return await call_next(request)

        client_id = self._get_client_id(request)
        if self._is_rate_limited(client_id):
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please try again later."},
            )

        response = await call_next(request)
        return response
