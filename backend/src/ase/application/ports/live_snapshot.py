"""Ports for the disposable live-store snapshot (ADR 0022), never a durable archive."""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from ase.domain.events import Event


@dataclass(frozen=True, slots=True)
class SnapshotLoad:
    """Validated public events from the snapshot; skipped counts invalid records only."""

    events: tuple[Event, ...] = ()
    skipped: int = 0


class LiveSnapshotStorage(Protocol):
    """Blocking file work. Callers run both methods off the event loop."""

    def read(self) -> SnapshotLoad:
        """Return validated events, or none when the file is absent, unsafe or damaged."""
        ...

    def write(self, events: Sequence[Event], saved_at: datetime) -> bool:
        """Atomically replace the snapshot. False leaves any previous file in place."""
        ...


class RestorableEventStore(Protocol):
    def retained(self) -> list[Event]:
        """References to every retained immutable event, captured on the event loop."""
        ...

    def restore(self, events: Iterable[Event], now: datetime) -> int:
        """Seed an empty store before feeds start, applying retention and budgets."""
        ...
