"""A short, bounded window of recent public bus messages for resuming live streams.

A browser whose stream ends (normally at access-token renewal) reconnects with the
last position it saw. When every public message after that position is still held
here, the stream replays them instead of the browser downloading a new snapshot.
The window is bounded by count, age and estimated bytes. Alerts and session signals
are never retained: they are private or per-user and are not replayed.
"""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable
from typing import NamedTuple

from ase.adapters.store.memory import estimate_bytes
from ase.application.ports.feeds import BusMessage
from ase.domain.events import Event

REPLAYABLE_KINDS = frozenset({"event.upsert", "event.expire", "event.resync", "source.health"})
MAX_REPLAY_MESSAGES = 1_000
MAX_REPLAY_AGE_SECONDS = 120.0
MAX_REPLAY_BYTES = 8 * 1024 * 1024
MESSAGE_OVERHEAD_BYTES = 256
EXPIRED_ID_BYTES = 64


def estimate_message_bytes(message: BusMessage) -> int:
    """Approximate the memory a retained message keeps alive."""
    size = MESSAGE_OVERHEAD_BYTES
    events = message.payload.get("events")
    if isinstance(events, list):
        size += sum(estimate_bytes(event) for event in events if isinstance(event, Event))
    ids = message.payload.get("ids")
    if isinstance(ids, tuple | list):
        size += EXPIRED_ID_BYTES * len(ids)
    return size


class _Entry(NamedTuple):
    recorded_at: float
    size: int
    message: BusMessage


class ReplayBuffer:
    def __init__(
        self,
        *,
        max_messages: int = MAX_REPLAY_MESSAGES,
        max_age_seconds: float = MAX_REPLAY_AGE_SECONDS,
        max_bytes: int = MAX_REPLAY_BYTES,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._max_messages = max_messages
        self._max_age = max_age_seconds
        self._max_bytes = max_bytes
        self._monotonic = monotonic
        self._entries: deque[_Entry] = deque()
        self._bytes = 0
        # The highest sequence discarded from the window. A position below it may have
        # missed a message that can no longer be replayed.
        self._floor = 0

    @property
    def size(self) -> int:
        return len(self._entries)

    @property
    def estimated_bytes(self) -> int:
        return self._bytes

    def record(self, message: BusMessage) -> None:
        if message.kind not in REPLAYABLE_KINDS:
            return
        size = estimate_message_bytes(message)
        self._entries.append(_Entry(self._monotonic(), size, message))
        self._bytes += size
        self._trim()

    def after(self, sequence: int) -> list[BusMessage] | None:
        """Retained messages published after `sequence`, or None when some are gone."""
        self._trim()
        if sequence < self._floor:
            return None
        return [entry.message for entry in self._entries if entry.message.sequence > sequence]

    def _trim(self) -> None:
        cutoff = self._monotonic() - self._max_age
        while self._entries and (
            len(self._entries) > self._max_messages
            or self._bytes > self._max_bytes
            or self._entries[0].recorded_at < cutoff
        ):
            entry = self._entries.popleft()
            self._bytes -= entry.size
            self._floor = entry.message.sequence
