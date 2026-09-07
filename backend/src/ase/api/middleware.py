"""Security headers on every response and a request body size cap (pure ASGI, stream safe)."""

from __future__ import annotations

import re

from fastapi import Request
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from ase.api.errors import PayloadTooLarge, handle_app_error

NO_STORE_PREFIXES = (
    "/api/auth",
    "/api/me",
    "/api/map",
    "/api/admin",
    "/api/events",
    "/api/stream",
    "/api/teams",
    "/api/direction",
    "/api/reports",
    "/api/research",
    "/api/report-search",
    "/api/warning",
    "/api/schedules",
    "/api/trackers/social",
)
DOCS_PREFIXES = ("/api/docs", "/api/openapi.json")
API_CSP = "default-src 'none'; frame-ancestors 'none'"
DEFAULT_MAX_BODY_BYTES = 64 * 1024
IMPORT_MAX_BODY_BYTES = 8 * 1024 * 1024
IMPORT_PATH = "/api/research/inputs"
_UUID_PATH = r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}"
ORIGINAL_UPLOAD_PATH = re.compile(
    rf"/api/reports/{_UUID_PATH}/original-assets/{_UUID_PATH}/content"
)
MAP_IMAGE_MAX_BODY_BYTES = 12 * 1024 * 1024
MAP_IMAGE_PATH = re.compile(rf"/api/map/views/{_UUID_PATH}/revisions/{_UUID_PATH}/image-package")
MAP_VIEW_MAX_BODY_BYTES = 6 * 1024 * 1024 + 16 * 1024
MAP_VIEW_REVISION_PATH = re.compile(
    r"/api/map/views/[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}"
)


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
                if path.startswith(NO_STORE_PREFIXES) and "no-store" not in headers.get(
                    "Cache-Control", ""
                ):
                    headers["Cache-Control"] = "no-store"
            await send(message)

        await self.app(scope, receive, send_with_headers)


class BodySizeLimitMiddleware:
    """Reject oversized bodies with 413 before the application sees them.

    Ordinary JSON is capped at 64 KiB; saved map state has a bounded larger allowance.
    Buffered bodies without Content-Length receive the same checks. Binary research
    imports stream through a separate guard. The proxy applies outer limits as well.
    """

    def __init__(self, app: ASGIApp, max_bytes: int = DEFAULT_MAX_BODY_BYTES) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        declared = Headers(scope=scope).get("content-length")
        importing = (scope.get("path") == IMPORT_PATH and scope.get("method") == "POST") or (
            scope.get("method") == "PUT"
            and ORIGINAL_UPLOAD_PATH.fullmatch(scope.get("path", "")) is not None
        )
        saving_map = (scope.get("path") == "/api/map/views" and scope.get("method") == "POST") or (
            scope.get("method") == "PATCH"
            and MAP_VIEW_REVISION_PATH.fullmatch(scope.get("path", "")) is not None
        )
        exporting_image = (
            scope.get("method") == "POST"
            and MAP_IMAGE_PATH.fullmatch(scope.get("path", "")) is not None
        )
        limit = (
            MAP_IMAGE_MAX_BODY_BYTES
            if exporting_image
            else IMPORT_MAX_BODY_BYTES
            if importing
            else MAP_VIEW_MAX_BODY_BYTES
            if saving_map
            else self.max_bytes
        )
        if declared is not None and declared.isdigit() and int(declared) > limit:
            await self._reject(scope, receive, send)
            return
        if importing or exporting_image:
            await self._stream_import(scope, receive, send, limit)
            return

        buffered: list[Message] = []
        total = 0
        while True:
            message = await receive()
            buffered.append(message)
            if message["type"] != "http.request":
                break
            total += len(message.get("body", b""))
            if total > limit:
                await self._reject(scope, receive, send)
                return
            if not message.get("more_body", False):
                break

        async def replay() -> Message:
            if buffered:
                return buffered.pop(0)
            return await receive()

        await self.app(scope, replay, send)

    async def _stream_import(self, scope: Scope, receive: Receive, send: Send, limit: int) -> None:
        """Authenticate upload routes before allocating a large request body.

        The route reads only after its identity dependencies succeed. Guard chunked
        input here as well as in the route; ordinary JSON requests keep the small cap.
        """
        total = 0
        started = False

        async def limited_receive() -> Message:
            nonlocal total
            message = await receive()
            if message["type"] == "http.request":
                total += len(message.get("body", b""))
                if total > limit:
                    raise PayloadTooLarge()
            return message

        async def tracked_send(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracked_send)
        except PayloadTooLarge:
            if started:
                raise
            await self._reject(scope, receive, send)

    async def _reject(self, scope: Scope, receive: Receive, send: Send) -> None:
        response = await handle_app_error(Request(scope), PayloadTooLarge())
        await response(scope, receive, send)
