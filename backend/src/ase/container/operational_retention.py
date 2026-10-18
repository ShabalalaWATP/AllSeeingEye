"""Optional independent housekeeping and its explicit transaction boundary."""

import asyncio
from datetime import datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ase.adapters.persistence.operational_retention import SqlOperationalRetention
from ase.application.ports import Clock
from ase.application.worker_progress import run_cycle
from ase.domain.operational_retention import OperationalRetentionPolicy

log = structlog.get_logger(__name__)


async def maintain_operations(
    sessions: async_sessionmaker[AsyncSession],
    now: datetime,
    policy: OperationalRetentionPolicy,
    *,
    dry_run: bool = True,
) -> dict[str, int]:
    async with sessions() as session:
        counts = await SqlOperationalRetention(session).sweep(now, policy, dry_run=dry_run)
        if not dry_run:
            await session.commit()
        return counts


async def run_operational_retention(
    sessions: async_sessionmaker[AsyncSession], clock: Clock, policy: OperationalRetentionPolicy
) -> None:
    async def cycle() -> None:
        counts = await maintain_operations(sessions, clock.now(), policy, dry_run=False)
        if any(counts.values()):
            log.info("operational_retention.completed", counts=counts)

    while True:
        try:
            await run_cycle("operational_retention", 60, cycle)
        except Exception:
            # SQL/validation errors can contain personal data. Counts only on success.
            log.warning("operational_retention.failed")
        await asyncio.sleep(60)
