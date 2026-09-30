"""Composition of process-local runtime measurements and bounded queue counts."""

from __future__ import annotations

import asyncio
import mmap
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.bus.memory import InMemoryEventBus
from ase.adapters.persistence.report_job_models import ReportJobRow
from ase.adapters.worker_health import LOOP_LAG_THRESHOLD_SECONDS, InMemoryWorkerHeartbeats, LoopLag

if TYPE_CHECKING:
    from ase.container import Container


@dataclass
class RuntimeHealth:
    workers: InMemoryWorkerHeartbeats = field(default_factory=InMemoryWorkerHeartbeats)
    lag: LoopLag = field(default_factory=LoopLag)
    _task: asyncio.Task[None] | None = None

    @property
    def ready(self) -> bool:
        return self.workers.ready and self.lag.p99_seconds <= LOOP_LAG_THRESHOLD_SECONDS

    def start(self) -> None:
        self._task = asyncio.create_task(self.lag.run(), name="runtime-loop-lag")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None


async def runtime_totals(container: Container, session: AsyncSession) -> dict[str, int | None]:
    store_count, store_bytes, store_budget = container.store.runtime_stats()
    bus = container.bus
    queued = await session.scalar(
        select(func.count()).select_from(ReportJobRow).where(ReportJobRow.status == "queued")
    )
    return {
        "bus_subscribers": bus.subscriber_count if isinstance(bus, InMemoryEventBus) else 0,
        "stream_drops": bus.dropped_count if isinstance(bus, InMemoryEventBus) else 0,
        "bus_queue_depth": bus.queue_depth if isinstance(bus, InMemoryEventBus) else 0,
        "read_rejections": container.store.read_rejections,
        "store_events": store_count,
        "store_bytes": store_bytes,
        "store_budget_bytes": store_budget,
        "rss_bytes": process_rss_bytes(),
        "job_queue_depth": queued or 0,
    }


def process_rss_bytes() -> int | None:
    """Current RSS on Linux (the deployment target); unavailable elsewhere."""
    try:
        pages = int(Path("/proc/self/statm").read_text(encoding="ascii").split()[1])
        return pages * mmap.PAGESIZE
    except (OSError, ValueError, IndexError, AttributeError):
        return None
