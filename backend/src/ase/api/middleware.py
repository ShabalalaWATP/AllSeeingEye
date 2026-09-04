"""Security headers on every response. Caddy adds HSTS and the SPA policy in production."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

NO_STORE_PREFIXES = ("/api/auth", "/api/me", "/api/admin")
DOCS_PREFIXES = ("/api/docs", "/api/openapi.json")
API_CSP = "default-src 'none'; frame-ancestors 'none'"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        headers = response.headers
        headers["X-Content-Type-Options"] = "nosniff"
        headers["Referrer-Policy"] = "no-referrer"
        headers["X-Frame-Options"] = "DENY"
        path = request.url.path
        if not path.startswith(DOCS_PREFIXES):
            headers["Content-Security-Policy"] = API_CSP
        if path.startswith(NO_STORE_PREFIXES):
            headers["Cache-Control"] = "no-store"
        return response
