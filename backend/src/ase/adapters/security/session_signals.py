"""In-process session change signals; valid because exactly one API process runs."""

from collections import OrderedDict
from collections.abc import Callable
from datetime import datetime, timedelta
from uuid import UUID

from ase.application.ports import Clock


class InMemorySessionSignals:
    """The latest committed change per user, kept long enough to outlive any cached check."""

    def __init__(
        self,
        clock: Clock,
        *,
        notify: Callable[[UUID], None] | None = None,
        retention: timedelta = timedelta(hours=1),
        capacity: int = 10_000,
    ) -> None:
        self._clock, self._notify = clock, notify
        self._retention, self._capacity = retention, capacity
        self._changes: OrderedDict[UUID, datetime] = OrderedDict()

    def publish(self, user_id: UUID) -> None:
        now = self._clock.now()
        self._changes[user_id] = now
        self._changes.move_to_end(user_id)
        oldest_kept = now - self._retention
        while self._changes and (
            len(self._changes) > self._capacity or next(iter(self._changes.values())) < oldest_kept
        ):
            self._changes.popitem(last=False)
        if self._notify is not None:
            self._notify(user_id)

    def changed_since(self, user_id: UUID, moment: datetime) -> bool:
        changed = self._changes.get(user_id)
        return changed is not None and changed >= moment
