"""Periodic physical expiry, independent of feed configuration and incoming requests."""

import asyncio

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ase.adapters.persistence.original_assets import SqlOriginalAssetRepository
from ase.adapters.persistence.users import SqlUserRepository
from ase.application.ports import Clock

log = structlog.get_logger(__name__)


async def expire_original_assets(
    sessions: async_sessionmaker[AsyncSession],
    clock: Clock,
) -> None:
    """An expired asset is unavailable immediately; physical rows are swept every minute."""
    while True:
        try:
            async with sessions() as session:
                await SqlUserRepository(session).lock_administration()
                await SqlOriginalAssetRepository(session).expire(clock.now())
                await session.commit()
        except Exception:
            # Do not expose database content or retained permitted-use declarations.
            log.warning("original_assets.expiry_failed")
        await asyncio.sleep(60)
