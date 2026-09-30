"""Recover a bounded lease page with one read and one compare-and-set update."""

from datetime import datetime

from sqlalchemy import and_, case, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.report_job_codec import from_row
from ase.adapters.persistence.report_job_models import ReportJobRow as Row
from ase.application.report_jobs.recovery import expired_failure


async def recover_expired(session: AsyncSession, now: datetime, limit: int) -> int:
    rows = list(
        await session.scalars(
            select(Row)
            .where(Row.status == "running", Row.lease_until <= now)
            .order_by(Row.lease_until, Row.id)
            .limit(limit)
            .execution_options(populate_existing=True)
        )
    )
    if not rows:
        return 0
    failures = {row.id: expired_failure(from_row(row).payload) for row in rows}
    recovered = await session.scalars(
        update(Row)
        .where(
            Row.status == "running",
            Row.lease_until <= now,
            Row.updated_at <= now,
            or_(*(and_(Row.id == row.id, Row.revision == row.revision) for row in rows)),
        )
        .values(
            status="paused",
            lease_token=None,
            lease_until=None,
            error=case(failures, value=Row.id),
            updated_at=now,
            revision=Row.revision + 1,
        )
        .returning(Row.id)
        .execution_options(synchronize_session=False)
    )
    # Count actual compare-and-set successes without materialising another list.
    return sum(1 for _ in recovered)
