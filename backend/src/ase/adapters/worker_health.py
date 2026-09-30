"""Bounded process-local progress and loop-lag measurements."""

import asyncio
import math
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from ase.application.ports.worker_health import WorkerError

OVERDUE_INTERVALS = 3
LOOP_LAG_THRESHOLD_SECONDS = 2.0
LOOP_SAMPLE_SECONDS = 1.0
MAX_WORKERS = 1000


@dataclass(frozen=True, slots=True)
class WorkerState:
    name: str
    expected_interval_seconds: float
    last_cycle: datetime | None
    last_error_code: WorkerError | None
    overdue: bool


@dataclass(slots=True)
class _Progress:
    interval: float
    at: float
    last_cycle: datetime | None = None
    error: WorkerError | None = None


class InMemoryWorkerHeartbeats:
    def __init__(self, *, monotonic: Callable[[], float] = time.monotonic) -> None:
        self._now = monotonic
        self._workers: dict[str, _Progress] = {}

    def register(self, name: str, expected_interval: float) -> None:
        if expected_interval <= 0 or not math.isfinite(expected_interval):
            raise ValueError("Worker intervals must be finite and positive")
        if name in self._workers:
            # A deliberate resume can shorten a source cooldown. Updating its
            # expected cadence must never fabricate a completed cycle.
            self._workers[name].interval = expected_interval
            return
        if len(self._workers) >= MAX_WORKERS:
            raise ValueError("Worker registry capacity exceeded")
        self._workers[name] = _Progress(expected_interval, self._now())

    def completed(
        self, name: str, expected_interval: float, error_code: WorkerError | None = None
    ) -> None:
        self.register(name, expected_interval)
        progress = self._workers[name]
        progress.interval, progress.at = expected_interval, self._now()
        progress.last_cycle, progress.error = datetime.now(UTC), error_code

    def snapshot(self) -> list[WorkerState]:
        now = self._now()
        return [
            WorkerState(
                name,
                entry.interval,
                entry.last_cycle,
                entry.error,
                now - entry.at > OVERDUE_INTERVALS * entry.interval,
            )
            for name, entry in sorted(self._workers.items())
        ]

    @property
    def ready(self) -> bool:
        return not any(worker.overdue for worker in self.snapshot())


class LoopLag:
    def __init__(self, *, monotonic: Callable[[], float] = time.monotonic) -> None:
        self._now = monotonic
        self._samples: deque[float] = deque(maxlen=120)
        self._last: float | None = None

    @property
    def p99_seconds(self) -> float:
        ordered = sorted(self._samples)
        sampled = ordered[max(0, math.ceil(len(ordered) * 0.99) - 1)] if ordered else 0
        # Readiness can run before the monitor resumes after an event-loop stall.
        current = (
            max(0, self._now() - self._last - LOOP_SAMPLE_SECONDS) if self._last is not None else 0
        )
        return max(sampled, current)

    async def run(self) -> None:
        self._last = self._now()
        while True:
            await asyncio.sleep(LOOP_SAMPLE_SECONDS)
            now = self._now()
            self._samples.append(max(0, now - self._last - LOOP_SAMPLE_SECONDS))
            self._last = now
