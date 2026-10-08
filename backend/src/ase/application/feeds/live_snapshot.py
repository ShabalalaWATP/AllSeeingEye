"""Restore the live store before feeds start, then save it on an interval (ADR 0022).

The snapshot is a disposable restart aid. Loading happens once; saving never runs
concurrently with itself and serialises off the event loop. A final save runs on
graceful shutdown only when the load completed, so an interrupted startup cannot
replace a good file with a partial store. Restored events are limited to sources
that are still registered and enabled, so a retired or disabled feed does not return
with a restart.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable, Collection, Sequence
from datetime import timedelta

from ase.application.feeds.cooperative_work import joined_thread_call
from ase.application.ports import Clock
from ase.application.ports.live_snapshot import (
    LiveSnapshotStorage,
    RestorableEventStore,
    SnapshotLoad,
)
from ase.application.ports.source_controls import SourceAdmission
from ase.application.worker_progress import register_worker, run_cycle
from ase.domain.events import Event

log = logging.getLogger(__name__)
Sleep = Callable[[float], Awaitable[None]]


class LiveStoreSnapshots:
    def __init__(
        self,
        store: RestorableEventStore,
        storage: LiveSnapshotStorage,
        clock: Clock,
        *,
        interval: timedelta,
        sleep: Sleep = asyncio.sleep,
        registered: Collection[str] | None = None,
        admission: SourceAdmission | None = None,
    ) -> None:
        self._store = store
        # None restores every source; production passes the configured connectors.
        self._registered = None if registered is None else frozenset(registered)
        self._admission = admission
        self._storage = storage
        self._clock = clock
        self._interval = interval.total_seconds()
        self._sleep = sleep
        self._saving = asyncio.Lock()
        self._task: asyncio.Task[None] | None = None
        self._loaded = False

    async def start(self) -> None:
        await self.load()
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        task, self._task = self._task, None
        if task is not None:
            task.cancel()
            # An in-flight save finishes its file work before the task ends.
            await asyncio.gather(task, return_exceptions=True)
        if self._loaded:
            await run_cycle("live_snapshot", self._interval, self.save)

    async def load(self) -> int:
        """Restore once; returns the number of snapshot events the store retained."""
        if self._loaded:
            return 0
        try:
            loaded = await joined_thread_call(self._storage.read)
        except Exception:
            # The storage adapter reports its own reasons; never block startup on it.
            log.warning("live_snapshot.load_failed")
            loaded = SnapshotLoad()
        admitted = await self._admitted(loaded.events)
        restored = self._store.restore(admitted, self._clock.now())
        self._loaded = True
        log.info(
            "live_snapshot.loaded read=%d restored=%d skipped=%d withheld=%d",
            len(loaded.events),
            restored,
            loaded.skipped,
            len(loaded.events) - len(admitted),
        )
        return restored

    async def _admitted(self, events: Sequence[Event]) -> Sequence[Event]:
        """Only currently registered and enabled sources come back; fail closed."""
        if self._registered is None:
            return events
        allowed = self._registered
        if self._admission is not None:
            try:
                enabled = await self._admission.enabled_many(tuple(sorted(allowed)))
            except Exception:
                log.warning("live_snapshot.admission_unavailable")
                return ()
            allowed = frozenset(source for source, on in enabled.items() if on)
        return tuple(event for event in events if event.source_id in allowed)

    async def save(self) -> bool:
        async with self._saving:
            # Capture immutable references on the loop; encode them in a worker thread.
            events = self._store.retained()
            saved_at = self._clock.now()
            try:
                return await joined_thread_call(lambda: self._storage.write(events, saved_at))
            except Exception:
                log.warning("live_snapshot.save_failed")
                return False

    async def _run(self) -> None:
        register_worker("live_snapshot", self._interval)
        while True:
            await self._sleep(self._interval)
            await run_cycle("live_snapshot", self._interval, self.save)
