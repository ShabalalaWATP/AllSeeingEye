"""In-memory sliding-window rate limiter, sized for a single-process deployment."""

from __future__ import annotations

import math
from collections import OrderedDict, deque

from ase.application.ports import Clock


class InMemorySlidingWindowLimiter:
    def __init__(self, clock: Clock, max_keys: int = 10_000) -> None:
        self._clock = clock
        self._max_keys = max_keys
        self._hits: OrderedDict[str, deque[float]] = OrderedDict()

    def hit(self, key: str, limit: int, window_seconds: int) -> int | None:
        now = self._clock.now().timestamp()
        window = self._hits.setdefault(key, deque())
        self._hits.move_to_end(key)  # least recently used keys are evicted first
        retry = self._retry_after(window, limit, window_seconds, now)
        if retry is not None:
            return retry
        window.append(now)
        self._evict_if_needed()
        return None

    def peek(self, key: str, limit: int, window_seconds: int) -> int | None:
        window = self._hits.get(key)
        if window is None:
            return None
        return self._retry_after(window, limit, window_seconds, self._clock.now().timestamp())

    @staticmethod
    def _retry_after(
        window: deque[float], limit: int, window_seconds: int, now: float
    ) -> int | None:
        cutoff = now - window_seconds
        while window and window[0] <= cutoff:
            window.popleft()
        if len(window) >= limit:
            return max(1, math.ceil(window[0] + window_seconds - now))
        return None

    def reset(self) -> None:
        self._hits.clear()

    def _evict_if_needed(self) -> None:
        # Bound memory under abuse: drop the least recently used keys once the table is full.
        while len(self._hits) > self._max_keys:
            self._hits.popitem(last=False)
