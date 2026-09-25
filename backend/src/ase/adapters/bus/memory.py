"""In-process fan-out: each subscriber gets a bounded queue; slow consumers lose old messages."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator

from ase.adapters.store.memory import estimate_bytes
from ase.application.ports.feeds import BusMessage
from ase.domain.events import Event

_CLOSE = BusMessage("__close__")
MAX_UPSERT_EVENTS = 500
# Leave room below the browser's 1 MiB byte cap for JSON escaping and framing.
MAX_UPSERT_BYTES = 384 * 1024


def _oversized_upsert(message: BusMessage) -> bool:
    events = message.payload.get("events")
    if message.kind != "event.upsert" or not isinstance(events, list):
        return False
    if len(events) > MAX_UPSERT_EVENTS:
        return True
    size = 0
    for event in events:
        if isinstance(event, Event):
            size += estimate_bytes(event)
            if size > MAX_UPSERT_BYTES:
                return True
    return False


class InMemorySubscription:
    def __init__(self, bus: InMemoryEventBus, max_queue: int) -> None:
        self._bus = bus
        self._queue: asyncio.Queue[BusMessage] = asyncio.Queue(maxsize=max_queue)
        self._closed = False
        self.dropped = 0
        self._resync_needed = False

    def push(self, message: BusMessage) -> None:
        if self._closed:
            return
        if self._queue.full():
            try:
                dropped = self._queue.get_nowait()
                self.dropped += 1
                if dropped.kind in {"event.upsert", "event.expire", "event.resync"}:
                    self._resync_needed = True
            except asyncio.QueueEmpty:  # pragma: no cover (race guard)
                pass
        self._queue.put_nowait(message)

    def __aiter__(self) -> AsyncIterator[BusMessage]:
        return self

    async def __anext__(self) -> BusMessage:
        if self._resync_needed:
            return self._resynchronise()
        if self._closed and self._queue.empty():
            raise StopAsyncIteration
        message = await self._queue.get()
        if self._resync_needed:
            return self._resynchronise(message)
        if message is _CLOSE:
            raise StopAsyncIteration
        return message

    def _resynchronise(self, first: BusMessage | None = None) -> BusMessage:
        self._resync_needed = False
        # Keep the gap outside the queue; discard pre-barrier live deltas so they
        # cannot overwrite a newer canonical snapshot, including after a waiting read.
        queued = [first] if first is not None else []
        while not self._queue.empty():
            queued.append(self._queue.get_nowait())
        for message in queued:
            if message.kind in {"event.upsert", "event.expire", "event.resync"}:
                self.dropped += 1
            else:
                self._queue.put_nowait(message)
        return BusMessage("event.resync", {"reason": "stream_gap"})

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._bus.unsubscribe(self)
        # Wake a consumer blocked on an empty queue; a full queue drains and then stops.
        with contextlib.suppress(asyncio.QueueFull):
            self._queue.put_nowait(_CLOSE)


class InMemoryEventBus:
    def __init__(self, max_queue: int = 128) -> None:
        self._max_queue = max_queue
        self._subscriptions: set[InMemorySubscription] = set()

    @property
    def subscriber_count(self) -> int:
        return len(self._subscriptions)

    def subscribe(self) -> InMemorySubscription:
        subscription = InMemorySubscription(self, self._max_queue)
        self._subscriptions.add(subscription)
        return subscription

    async def publish(self, message: BusMessage) -> None:
        self.publish_nowait(message)

    def publish_nowait(self, message: BusMessage) -> None:
        """Fan out without awaiting, for synchronous hooks such as a commit listener."""
        # A sensor batch may contain tens of thousands of immutable events. Never
        # retain or serialise that batch per slow browser: reload its bounded snapshot.
        if _oversized_upsert(message):
            message = BusMessage("event.resync", {"reason": "snapshot_required"})
        for subscription in list(self._subscriptions):
            subscription.push(message)

    def unsubscribe(self, subscription: InMemorySubscription) -> None:
        self._subscriptions.discard(subscription)
