"""Unbuffered ASGI request correlation and one completion event per request."""

import asyncio
import re
from time import perf_counter
from uuid import uuid4

import structlog
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from ase.api.errors import handle_unexpected
from ase.api.middleware import SecurityHeadersMiddleware
from ase.infrastructure.request_context import request_context

log = structlog.get_logger(__name__)
SAFE_ID = re.compile(rb"[A-Za-z0-9-]{8,64}\Z")
METHODS = frozenset({"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE"})


class RequestLoggingMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        ids = [value for name, value in scope["headers"] if name.lower() == b"x-request-id"]
        identifier = (
            ids[0].decode("ascii") if len(ids) == 1 and SAFE_ID.fullmatch(ids[0]) else uuid4().hex
        )
        token = request_context.set((asyncio.current_task(), identifier))
        prior = structlog.contextvars.get_contextvars()
        structlog.contextvars.clear_contextvars()
        start, status, outcome = perf_counter(), None, "incomplete"
        started = False

        async def received() -> Message:
            nonlocal outcome
            message = await receive()
            if message["type"] == "http.disconnect":
                outcome = "disconnected"
            return message

        async def sent(message: Message) -> None:
            nonlocal started, status, outcome
            if message["type"] == "http.response.start":
                status, started = message["status"], True
                headers = [
                    (name, value)
                    for name, value in message.get("headers", [])
                    if name.lower() != b"x-request-id"
                ]
                message = {**message, "headers": [*headers, (b"x-request-id", identifier.encode())]}
            await send(message)
            if (
                message["type"] == "http.response.body"
                and not message.get("more_body", False)
                and outcome != "disconnected"
            ):
                outcome = "error" if status is not None and status >= 500 else "completed"

        try:
            await self.app(scope, received, sent)
        except asyncio.CancelledError:
            outcome = "cancelled"
            raise
        except Exception as exc:
            outcome = "error"
            if started:
                # Headers/body may already be on the wire; never attempt a second response.
                raise
            response = await handle_unexpected(Request(scope), exc)
            await SecurityHeadersMiddleware(response)(scope, received, sent)
        finally:
            route = scope.get("route")
            log.info(
                "request.complete",
                request_id=identifier,
                method=scope["method"] if scope["method"] in METHODS else "OTHER",
                route=getattr(route, "path", "unmatched"),
                status=status,
                duration_ms=round((perf_counter() - start) * 1000, 3),
                outcome=outcome,
            )
            request_context.reset(token)
            structlog.contextvars.clear_contextvars()
            structlog.contextvars.bind_contextvars(**prior)
