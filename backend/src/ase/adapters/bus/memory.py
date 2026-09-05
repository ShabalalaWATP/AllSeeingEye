"""In-process fan-out: each subscriber gets a bounded queue; slow consumers lose old messages."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator

from ase.application.ports.feeds import BusMessage

_CLOSE = BusMessage("__close__")


class InMemorySubscription:
    def __init__(self, bus: InMemoryEventBus, max_queue: int) -> None:
        self._bus = bus
        self._queue: asyncio.Queue[BusMessage] = asyncio.Queue(maxsize=max_queue)
        self._closed = False
        self.dropped = 0

    def push(self, message: BusMessage) -> None:
        if self._closed:
            return
        if self._queue.full():
            try:
                self._queue.get_nowait()
                self.dropped += 1
            except asyncio.QueueEmpty:  # pragma: no cover (race guard)
                pass
        self._queue.put_nowait(message)

    def __aiter__(self) -> AsyncIterator[BusMessage]:
        return self

    async def __anext__(self) -> BusMessage:
        if self._closed and self._queue.empty():
            raise StopAsyncIteration
        message = await self._queue.get()
        if message is _CLOSE:
            raise StopAsyncIteration
        return message

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._bus.unsubscribe(self)
        # Wake a consumer blocked on an empty queue; a full queue drains and then stops.
        with contextlib.suppress(asyncio.QueueFull):
            self._queue.put_nowait(_CLOSE)


class InMemoryEventBus:
    def __init__(self, max_queue: int = 1_000) -> None:
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
        for subscription in list(self._subscriptions):
            subscription.push(message)

    def unsubscribe(self, subscription: InMemorySubscription) -> None:
        self._subscriptions.discard(subscription)
