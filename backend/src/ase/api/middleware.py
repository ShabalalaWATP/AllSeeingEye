"""Security headers on every response and a request body size cap (pure ASGI, stream safe)."""

from __future__ import annotations

from fastapi import Request
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from ase.api.errors import PayloadTooLarge, handle_app_error

NO_STORE_PREFIXES = ("/api/auth", "/api/me", "/api/admin", "/api/events", "/api/stream")
DOCS_PREFIXES = ("/api/docs", "/api/openapi.json")
API_CSP = "default-src 'none'; frame-ancestors 'none'"
DEFAULT_MAX_BODY_BYTES = 64 * 1024


class SecurityHeadersMiddleware:
    """Adds the API's headers to every HTTP response without buffering streamed bodies."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = str(scope.get("path", ""))

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["X-Content-Type-Options"] = "nosniff"
                headers["Referrer-Policy"] = "no-referrer"
                headers["X-Frame-Options"] = "DENY"
                if not path.startswith(DOCS_PREFIXES):
                    headers["Content-Security-Policy"] = API_CSP
                if path.startswith(NO_STORE_PREFIXES):
                    headers["Cache-Control"] = "no-store"
            await send(message)

        await self.app(scope, receive, send_with_headers)


class BodySizeLimitMiddleware:
    """Reject oversized bodies with 413 before the application sees them.

    The body is buffered up to the cap (a few tens of kilobytes) and replayed to the app,
    so streamed bodies without a Content-Length are covered too. Caddy enforces the same
    cap at the edge; this protects direct access to the API.
    """

    def __init__(self, app: ASGIApp, max_bytes: int = DEFAULT_MAX_BODY_BYTES) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        declared = Headers(scope=scope).get("content-length")
        if declared is not None and declared.isdigit() and int(declared) > self.max_bytes:
            await self._reject(scope, receive, send)
            return

        buffered: list[Message] = []
        total = 0
        while True:
            message = await receive()
            buffered.append(message)
            if message["type"] != "http.request":
                break
            total += len(message.get("body", b""))
            if total > self.max_bytes:
                await self._reject(scope, receive, send)
                return
            if not message.get("more_body", False):
                break

        async def replay() -> Message:
            if buffered:
                return buffered.pop(0)
            return await receive()

        await self.app(scope, replay, send)

    async def _reject(self, scope: Scope, receive: Receive, send: Send) -> None:
        response = await handle_app_error(Request(scope), PayloadTooLarge())
        await response(scope, receive, send)
