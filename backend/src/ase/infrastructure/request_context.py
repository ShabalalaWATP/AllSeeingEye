"""Task-owned correlation: inherited background contexts never claim a request."""

import asyncio
from contextvars import ContextVar

request_context: ContextVar[tuple[asyncio.Task[object] | None, str] | None] = ContextVar(
    "request_context", default=None
)


def request_id() -> str | None:
    context = request_context.get()
    if context is None:
        return None
    try:
        owner = asyncio.current_task()
    except RuntimeError:
        return None
    return context[1] if context[0] is owner else None
