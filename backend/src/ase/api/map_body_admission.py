"""Authenticate and bound saved-map JSON before FastAPI reads its typed body.

Admission is per application process: four saves in total and one per account.
Slots cover body intake and downstream parsing/persistence, so database waits cannot
accumulate parsed map state outside the budget. Route authentication and report-level
authorisation still run afterwards, including session revocation during the upload.
"""

from __future__ import annotations

import asyncio
import re
from uuid import UUID

from fastapi import Request
from starlette._utils import get_route_path
from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from ase.api.deps import bearer_scheme, get_container, get_current_user
from ase.api.errors import PayloadTooLarge, handle_app_error
from ase.domain.errors import AppError, InvalidRequest, RateLimited

MAX_CONCURRENT_MAP_SAVES = 4
MAP_BODY_READ_TIMEOUT_SECONDS = 30.0
MAP_VIEW_MAX_BODY_BYTES = 6 * 1024 * 1024 + 16 * 1024
_MAP_VIEW_ITEM_PATH = re.compile(r"/api/map/views/[^/]+")
_MAP_VIEW_UUID_PATH = re.compile(
    r"/api/map/views/[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}"
)


def saved_map_body_limit(scope: Scope, ordinary_limit: int) -> int | None:
    """Cover the router's full path shape without widening noncanonical body limits."""
    path = get_route_path(scope)
    if scope.get("method") == "POST" and path == "/api/map/views":
        return MAP_VIEW_MAX_BODY_BYTES
    if scope.get("method") == "PATCH" and _MAP_VIEW_ITEM_PATH.fullmatch(path):
        if _MAP_VIEW_UUID_PATH.fullmatch(path):
            return MAP_VIEW_MAX_BODY_BYTES
        # FastAPI accepts multiple UUID representations. Admission must also cover
        # these, even when the configured ordinary allowance exceeds the map cap.
        return min(ordinary_limit, MAP_VIEW_MAX_BODY_BYTES)
    return None


async def authenticated_map_user(scope: Scope) -> UUID:
    request = Request(scope)
    user = await get_current_user(get_container(request), await bearer_scheme(request))
    return user.id


class SavedMapBodyMiddleware:
    """One shared, non-waiting budget for every saved-map mutation representation."""

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes
        self._active: set[UUID] = set()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        limit = saved_map_body_limit(scope, self.max_bytes)
        if limit is None:
            await self.app(scope, receive, send)
            return
        try:
            user_id = await authenticated_map_user(scope)
            if user_id in self._active or len(self._active) >= MAX_CONCURRENT_MAP_SAVES:
                raise RateLimited(1)
        except AppError as exc:
            await self._reject(scope, receive, send, exc)
            return

        # No await between checking and claiming: requests cannot interleave here.
        self._active.add(user_id)
        try:
            try:
                declared = Headers(scope=scope).get("content-length")
                if declared is not None and declared.isdigit() and int(declared) > limit:
                    raise PayloadTooLarge()
                body = await self._read_body(receive, limit)
            except AppError as exc:
                await self._reject(scope, receive, send, exc)
                return
            if body is None:
                return  # A disconnected client must not reach parsing or persistence.

            async def replay() -> Message:
                nonlocal body
                if body is not None:
                    message = {"type": "http.request", "body": body, "more_body": False}
                    body = None
                    return message
                return await receive()

            await self.app(scope, replay, send)
        finally:
            self._active.discard(user_id)

    async def _read_body(self, receive: Receive, limit: int) -> bytes | None:
        buffer = bytearray()
        loop = asyncio.get_running_loop()
        deadline = loop.time() + MAP_BODY_READ_TIMEOUT_SECONDS
        try:
            async with asyncio.timeout_at(deadline):
                while True:
                    message = await receive()
                    # Also bound streams whose receive() returns without suspending.
                    if loop.time() >= deadline:
                        raise TimeoutError
                    if message["type"] == "http.disconnect":
                        return None
                    chunk = message.get("body", b"")
                    if len(buffer) + len(chunk) > limit:
                        raise PayloadTooLarge()
                    buffer.extend(chunk)
                    if not message.get("more_body", False):
                        return bytes(buffer)
        except TimeoutError as exc:
            raise InvalidRequest("The saved-map upload timed out.") from exc
        finally:
            buffer.clear()

    @staticmethod
    async def _reject(scope: Scope, receive: Receive, send: Send, exc: AppError) -> None:
        response = await handle_app_error(Request(scope), exc)
        await response(scope, receive, send)
