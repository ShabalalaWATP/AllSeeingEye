"""Thin research progress pages: scope, status and origin filters precede the limit."""

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from ase.adapters.persistence.access import visibility_predicate
from ase.adapters.persistence.report_job_codec import with_summary
from ase.adapters.persistence.report_job_models import ReportJobRow as Row
from ase.adapters.persistence.report_origin import job_origin
from ase.domain.access import Visibility
from ase.domain.report_jobs import ReportJob, job_timestamp


async def list_job_page(
    session: AsyncSession,
    visibility: Visibility,
    *,
    limit: int,
    statuses: Sequence[str] | None = None,
    include_briefings: bool = False,
    after: tuple[datetime, UUID] | None = None,
) -> list[ReportJob]:
    if type(limit) is not int or not 1 <= limit <= 101:
        raise ValueError("Use a bounded report job page.")
    query = (
        select(Row)
        .options(defer(Row.payload))
        .where(visibility_predicate(Row.owner_id, Row.team_id, visibility))
    )
    if statuses is not None:
        query = query.where(Row.status.in_(tuple(statuses)))
    if not include_briefings:
        query = query.where(job_origin(session) != "briefing")
    if after is not None:
        created_at, job_id = after
        job_timestamp(created_at)
        query = query.where(
            or_(Row.created_at < created_at, and_(Row.created_at == created_at, Row.id > job_id))
        )
    rows = await session.scalars(
        query.order_by(Row.created_at.desc(), Row.id)
        .limit(limit)
        .execution_options(populate_existing=True)
    )
    return [with_summary(row, row.summary) for row in rows]
