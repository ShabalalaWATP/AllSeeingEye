"""One open live stream: resume or start, replay, re-validation and frame ids.

The router supplies the session read and the payload encoder so authorisation stays
where it is defined. Replayed messages go through the same deadline and session
checks as live ones.
"""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import AsyncGenerator, Awaitable, Callable
from datetime import datetime, timedelta
from typing import Any, Literal

import anyio

from ase.api.stream_encoding import dumps
from ase.api.stream_resume import StreamCursor, parse_event_id
from ase.application.access import AccessContext
from ase.application.dto import AccessClaims
from ase.application.ports.feeds import BusMessage, Subscription
from ase.application.ports.session import SESSION_CHANGED
from ase.container import Container

AccessReader = Callable[[], Awaitable[AccessContext | None]]
MessageEncoder = Callable[[BusMessage], Awaitable[str | None]]
Frame = dict[str, str]


def access_signature(access: AccessContext) -> tuple[Any, ...]:
    return (
        access.actor.role,
        sorted((str(key), role.value) for key, role in access.memberships.items()),
        sorted((str(key), team.is_active) for key, team in access.teams.items()),
    )


class LiveStream:
    def __init__(
        self,
        container: Container,
        claims: AccessClaims,
        *,
        deadline: datetime,
        expires_in: int,
        ping_seconds: float,
        read_access: AccessReader,
        encode: MessageEncoder,
        shutdown_event: anyio.Event,
    ) -> None:
        self._container = container
        self._clock = container.clock
        self._claims = claims
        self._deadline = deadline
        self._expires_in = expires_in
        self._ping_seconds = ping_seconds
        self._read_access = read_access
        self._encode = encode
        self._shutdown_event = shutdown_event
        self._pending: deque[BusMessage] = deque()
        self._signature: tuple[Any, ...] = ()
        self._checked_at = self._clock.now()

    async def frames(self, last_event_id: str | None) -> AsyncGenerator[Frame]:
        bus = self._container.bus
        subscription = bus.subscribe()
        # No await separates subscribing from reading the replay window, so each
        # missed public message is either replayed or queued, never both or neither.
        start = bus.last_sequence
        requested = parse_event_id(last_event_id)
        backlog = None if requested is None else bus.replay(requested.epoch, requested.sequence)
        self._pending.extend(backlog or ())
        position = requested.sequence if requested is not None and self._pending else start
        interval = timedelta(seconds=self._ping_seconds)
        cursor = StreamCursor(bus.epoch, position, self._clock.now(), interval)
        try:
            self._checked_at = self._clock.now()
            access = await self._read_access()
            if access is None:
                yield {"event": "bye", "data": dumps({"reason": "session_revoked"})}
                return
            self._signature = access_signature(access)
            hello = {"expires_in": self._expires_in, "resumed": backlog is not None}
            yield cursor.frame("hello", dumps(hello), self._clock.now())
            if last_event_id and backlog is None:
                resync = dumps({"reason": "snapshot_required"})
                yield cursor.frame("event.resync", resync, self._clock.now())
            while not self._expired():
                if self._shutdown_event.is_set():
                    return
                replayed = bool(self._pending)
                if replayed:
                    message: BusMessage | None = self._pending.popleft()
                else:
                    try:
                        message = await self._receive(subscription)
                    except StopAsyncIteration:
                        return
                if self._expired():
                    break
                status = await self._recheck()
                if status == "revoked":
                    yield self._bye(cursor, "session_revoked")
                    return
                if status == "changed":
                    yield cursor.frame("access.changed", "{}", self._clock.now())
                frame = await self._frame(cursor, message, replayed and not self._pending, start)
                if frame is not None:
                    yield frame
            yield self._bye(cursor, "token_expired")
        finally:
            subscription.close()

    def _expired(self) -> bool:
        return self._clock.now() >= self._deadline

    async def _receive(self, subscription: Subscription) -> BusMessage | None:
        # A shutdown signal must wake idle streams before the response's short
        # grace period expires, allowing its terminal ASGI body to be sent.
        remaining = (self._deadline - self._clock.now()).total_seconds()
        message = asyncio.ensure_future(anext(aiter(subscription)))
        stopping = asyncio.create_task(self._shutdown_event.wait())
        try:
            finished, _ = await asyncio.wait(
                (message, stopping),
                timeout=max(0, min(remaining, self._ping_seconds)),
                return_when=asyncio.FIRST_COMPLETED,
            )
            if stopping in finished:
                raise StopAsyncIteration
            return message.result() if message in finished else None
        finally:
            message.cancel()
            stopping.cancel()
            # Client disconnect cancels an AnyIO task group. Join both waiters
            # without swallowing that cancellation or leaving queue readers behind.
            with anyio.CancelScope(shield=True):
                await asyncio.gather(message, stopping, return_exceptions=True)

    async def _recheck(self) -> Literal["revoked", "changed"] | None:
        # Public deliveries reuse a check until the recheck window passes or a
        # committed session change is signalled; alerts still re-read access in
        # _authorised_payload (api/routers/stream.py) before they are encoded.
        # An alert's own re-read does not reset this window, which only costs a read.
        freshness = self._container.session_freshness
        if not freshness.is_due(self._claims.user_id, self._checked_at):
            return None
        self._checked_at = self._clock.now()
        access = await self._read_access()
        if access is None:
            return "revoked"
        signature = access_signature(access)
        if signature == self._signature:
            return None
        self._signature = signature
        return "changed"

    async def _frame(
        self, cursor: StreamCursor, message: BusMessage | None, replay_ended: bool, start: int
    ) -> Frame | None:
        data = None
        if message is not None:
            cursor.advance(message.sequence)
            if replay_ended:
                cursor.advance(start)  # Nothing else up to here can be replayed.
            if message.kind != SESSION_CHANGED:
                data = await self._encode(message)
        now = self._clock.now()
        if message is not None and data is not None:
            return cursor.frame(message.kind, data, now)
        return cursor.checkpoint(now, idle=message is None)

    def _bye(self, cursor: StreamCursor, reason: str) -> Frame:
        return cursor.frame("bye", dumps({"reason": reason}), self._clock.now())
