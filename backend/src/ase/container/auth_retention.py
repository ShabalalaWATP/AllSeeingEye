"""Optional independent housekeeping and the transaction boundary used by the CLI."""

import asyncio
from datetime import datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ase.adapters.persistence.auth_retention import SqlAuthRetention
from ase.application.ports import Clock
from ase.application.worker_progress import run_cycle
from ase.domain.auth_retention import AuthRetentionPolicy

log = structlog.get_logger(__name__)


async def maintain_authentication(
    sessions: async_sessionmaker[AsyncSession],
    now: datetime,
    policy: AuthRetentionPolicy,
    *,
    dry_run: bool = True,
) -> dict[str, int]:
    async with sessions() as session:
        counts = await SqlAuthRetention(session).sweep(now, policy, dry_run=dry_run)
        if not dry_run:
            await session.commit()
        return counts


async def run_auth_retention(
    sessions: async_sessionmaker[AsyncSession], clock: Clock, policy: AuthRetentionPolicy
) -> None:
    async def cycle() -> None:
        counts = await maintain_authentication(sessions, clock.now(), policy, dry_run=False)
        if any(counts.values()):
            log.info("auth_retention.completed", counts=counts)

    while True:
        try:
            await run_cycle("auth_retention", 60, cycle)
        except Exception:
            # SQL errors can include identity or credential material. Do not log them.
            log.warning("auth_retention.failed")
        await asyncio.sleep(60)
