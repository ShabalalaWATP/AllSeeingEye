"""Return a live stream's per-user slot exactly once, however its response ends.

The route reserves the slot before it returns the response, and the body generator's
`finally` alone cannot be trusted to give it back. A client that disconnects while the
response is starting makes sse-starlette cancel its task group before the generator's
first iteration, and a never-started async generator never runs its `finally`. The
response therefore releases the slot when its ASGI call ends, and the generator still
releases it when it is consumed directly. Whichever comes first wins; the other is a no-op.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sse_starlette.sse import EventSourceResponse
from starlette.types import Receive, Scope, Send


class ReleaseOnce:
    """An idempotent wrapper, so two release paths can never free a slot twice."""

    def __init__(self, release: Callable[[], None]) -> None:
        self._release: Callable[[], None] | None = release

    @property
    def released(self) -> bool:
        return self._release is None

    def __call__(self) -> None:
        release, self._release = self._release, None
        if release is not None:
            release()


class SlotReleasingResponse(EventSourceResponse):
    """An SSE response that returns its stream slot when the ASGI call ends."""

    def __init__(self, content: Any, *, release: ReleaseOnce, **options: Any) -> None:
        super().__init__(content, **options)
        self._release_slot = release

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        try:
            await super().__call__(scope, receive, send)
        finally:
            self._release_slot()
