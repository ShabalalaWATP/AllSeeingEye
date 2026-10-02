"""Count authorised retained records over the saved half-open digest interval."""

from collections.abc import Awaitable, Callable
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.access import visibility_predicate
from ase.adapters.persistence.operational_models import AlertRow
from ase.adapters.persistence.report_job_models import ReportJobRow
from ase.domain.access import Visibility
from ase.domain.notification_digest import DigestCounts

ReviewCounter = Callable[
    [AsyncSession, Visibility, datetime, datetime], Awaitable[tuple[int, bool]]
]


async def digest_counts(
    session: AsyncSession,
    visibility: Visibility,
    since: datetime,
    until: datetime,
    reviews: ReviewCounter,
) -> DigestCounts:
    alerts = await session.scalar(
        select(func.count())
        .select_from(AlertRow)
        .where(
            visibility_predicate(AlertRow.created_by, AlertRow.team_id, visibility),
            AlertRow.fired_at >= since,
            AlertRow.fired_at < until,
        )
    )
    jobs: dict[str, int] = dict(
        (
            await session.execute(
                select(ReportJobRow.status, func.count())
                .where(
                    visibility_predicate(ReportJobRow.owner_id, ReportJobRow.team_id, visibility),
                    ReportJobRow.updated_at >= since,
                    ReportJobRow.updated_at < until,
                    ReportJobRow.status.in_(("completed", "needs_review", "failed")),
                )
                .group_by(ReportJobRow.status)
            )
        )
        .tuples()
        .all()
    )
    count, truncated = await reviews(session, visibility, since, until)
    return DigestCounts(
        alerts or 0,
        jobs.get("completed", 0) + jobs.get("needs_review", 0),
        jobs.get("failed", 0),
        count,
        truncated,
    )
