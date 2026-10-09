"""Bounded enquiry erasure for the existing housekeeping cycle."""

from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.admin_enquiries import SqlAdminEnquiryRepository
from ase.application.ports import Clock

PURGE_BATCH_SIZE = 100


async def purge_enquiries(session: AsyncSession, clock: Clock, retention_days: int) -> int:
    """Caller holds the administration guard and commits the entire housekeeping cycle."""
    return await SqlAdminEnquiryRepository(session).purge(
        clock.now() - timedelta(days=retention_days), PURGE_BATCH_SIZE
    )
