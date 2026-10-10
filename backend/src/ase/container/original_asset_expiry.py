"""Periodic physical expiry, independent of feed configuration and incoming requests."""

import asyncio

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ase.adapters.persistence.original_assets import SqlOriginalAssetRepository
from ase.adapters.persistence.original_passages import SqlOriginalPassageRepository
from ase.adapters.persistence.users import SqlUserRepository
from ase.application.ports import Clock
from ase.application.worker_progress import run_cycle
from ase.container.enquiry_retention import purge_enquiries

log = structlog.get_logger(__name__)


async def expire_original_assets(
    sessions: async_sessionmaker[AsyncSession],
    clock: Clock,
    enquiry_retention_days: int = 365,
) -> None:
    """An expired asset is unavailable immediately; physical rows are swept every minute."""

    async def cycle() -> None:
        async with sessions() as session:
            await SqlUserRepository(session).lock_administration()
            await SqlOriginalAssetRepository(session).expire(clock.now())
            await SqlOriginalPassageRepository(session).expire(clock.now())
            purged = await purge_enquiries(session, clock, enquiry_retention_days)
            await session.commit()
            if purged:
                log.info("enquiries.expired", count=purged)

    while True:
        try:
            await run_cycle("asset_expiry", 60, cycle)
        except Exception:
            # Do not expose database content or retained permitted-use declarations.
            log.warning("original_assets.expiry_failed")
        await asyncio.sleep(60)
