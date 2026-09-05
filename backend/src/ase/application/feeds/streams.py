"""Caps how many live streams one user may hold open at once."""

from __future__ import annotations

from collections import Counter
from uuid import UUID

DEFAULT_MAX_STREAMS_PER_USER = 4


class StreamLimiter:
    def __init__(self, max_per_user: int = DEFAULT_MAX_STREAMS_PER_USER) -> None:
        self._max = max_per_user
        self._open: Counter[UUID] = Counter()

    def acquire(self, user_id: UUID) -> bool:
        """Reserve a slot; False when the user already holds the maximum."""
        if self._open[user_id] >= self._max:
            return False
        self._open[user_id] += 1
        return True

    def release(self, user_id: UUID) -> None:
        if self._open[user_id] <= 1:
            self._open.pop(user_id, None)
        else:
            self._open[user_id] -= 1

    def held(self, user_id: UUID) -> int:
        return self._open[user_id]
