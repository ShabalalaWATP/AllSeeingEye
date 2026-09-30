"""Lease-only renewal, fenced against status, ownership, expiry and payload revision."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.report_job_models import ReportJobRow as Row
from ase.domain.report_jobs import ReportJob, job_lease


async def renew_lease(
    session: AsyncSession, job: ReportJob, token: UUID, now: datetime, until: datetime
) -> bool:
    job_lease(now, until)
    changed = await session.scalar(
        update(Row)
        .where(
            Row.id == job.id,
            Row.revision == job.revision,
            Row.status == "running",
            Row.lease_token == token,
            Row.lease_until > now,
            Row.updated_at <= now,
        )
        .values(lease_until=until)
        .returning(Row.id)
        .execution_options(synchronize_session=False)
    )
    return changed is not None
