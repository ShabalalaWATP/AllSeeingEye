"""Share one selection and DTO build among identical concurrent public live-event reads.

Many browsers ask for the same bounded snapshot after a bulk feed update. A read is
keyed by its normalised query and the store generation it started from, so any
mutation, expiry, regrade or source change produces a new key. Only public results
belong here: callers keep their own authorisation, admission and release checks, and
a failure in one caller's read is never handed to another caller.
"""

from __future__ import annotations

import asyncio
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable, Hashable
from typing import Final

from ase.domain.errors import RateLimited

MAX_SHARED_RESULTS: Final = 4
SHARED_RESULT_SECONDS: Final = 2.0
# Matches the store's per-actor read admission, so sharing never widens one actor's
# concurrent responses beyond what it could already request.
MAX_READS_PER_ACTOR: Final = 2


class _Failed:
    """The leading read failed; each waiting caller then reads for itself."""


_FAILED: Final = _Failed()


class SharedReads[V]:
    """Single-flight reads with a small, short-lived cache of completed results."""

    def __init__(
        self,
        *,
        max_results: int = MAX_SHARED_RESULTS,
        ttl_seconds: float = SHARED_RESULT_SECONDS,
        max_per_actor: int = MAX_READS_PER_ACTOR,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        if max_results < 0 or ttl_seconds < 0:
            raise ValueError("Shared read bounds must not be negative")
        self._max_results = max_results
        self._ttl = ttl_seconds
        self._max_per_actor = max_per_actor
        self._actors: dict[str, int] = {}
        self._monotonic = monotonic
        self._results: OrderedDict[Hashable, tuple[float, V]] = OrderedDict()
        self._pending: dict[Hashable, asyncio.Future[V | _Failed]] = {}
        # Observable counts for tests and benchmarks.
        self.loads = 0
        self.shared = 0

    def __len__(self) -> int:
        return len(self._results)

    async def read(
        self,
        key: Hashable,
        load: Callable[[], Awaitable[V]],
        *,
        actor: str,
        current: Callable[[], bool] = lambda: True,
    ) -> V:
        """The result for `key`, loading it once however many callers ask at the same time.

        `current` is checked after the load: a result whose source changed meanwhile is
        still returned to the callers that shared it but is not kept for later ones.
        """
        held = self._actors.get(actor, 0)
        if held >= self._max_per_actor:
            raise RateLimited(1)
        self._actors[actor] = held + 1
        try:
            return await self._read(key, load, current)
        finally:
            remaining = self._actors[actor] - 1
            if remaining:
                self._actors[actor] = remaining
            else:
                del self._actors[actor]

    async def _read(
        self, key: Hashable, load: Callable[[], Awaitable[V]], current: Callable[[], bool]
    ) -> V:
        cached = self._cached(key)
        if cached is not None:
            self.shared += 1
            return cached[1]
        pending = self._pending.get(key)
        if pending is not None:
            self.shared += 1
            # Shielded so one waiting caller's cancellation never cancels the shared read.
            outcome = await asyncio.shield(pending)
            return await load() if isinstance(outcome, _Failed) else outcome
        future: asyncio.Future[V | _Failed] = asyncio.get_running_loop().create_future()
        self._pending[key] = future
        self.loads += 1
        try:
            value = await load()
        except BaseException:
            future.set_result(_FAILED)
            raise
        finally:
            if self._pending.get(key) is future:
                del self._pending[key]
        future.set_result(value)
        if current():
            self._remember(key, value)
        return value

    def _cached(self, key: Hashable) -> tuple[float, V] | None:
        now = self._monotonic()
        for stale in [k for k, (at, _) in self._results.items() if now - at > self._ttl]:
            del self._results[stale]
        cached = self._results.get(key)
        if cached is not None:
            self._results.move_to_end(key)
        return cached

    def _remember(self, key: Hashable, value: V) -> None:
        if self._max_results == 0:
            return
        self._results[key] = (self._monotonic(), value)
        self._results.move_to_end(key)
        while len(self._results) > self._max_results:
            self._results.popitem(last=False)
