"""In-memory sliding-window rate limiter, sized for a single-process deployment."""

from __future__ import annotations

import math
from collections import deque

from ase.application.ports import Clock


class InMemorySlidingWindowLimiter:
    def __init__(self, clock: Clock, max_keys: int = 10_000) -> None:
        self._clock = clock
        self._max_keys = max_keys
        self._hits: dict[str, deque[float]] = {}

    def hit(self, key: str, limit: int, window_seconds: int) -> int | None:
        now = self._clock.now().timestamp()
        window = self._hits.setdefault(key, deque())
        cutoff = now - window_seconds
        while window and window[0] <= cutoff:
            window.popleft()
        if len(window) >= limit:
            return max(1, math.ceil(window[0] + window_seconds - now))
        window.append(now)
        self._evict_if_needed()
        return None

    def reset(self) -> None:
        self._hits.clear()

    def _evict_if_needed(self) -> None:
        # Bound memory under abuse: drop the oldest keys once the table is too large.
        while len(self._hits) > self._max_keys:
            oldest = next(iter(self._hits))
            del self._hits[oldest]
