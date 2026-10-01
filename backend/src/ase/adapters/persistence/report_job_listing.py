"""Thin research progress pages: scope, status and origin filters precede the limit."""

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, and_, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from ase.adapters.persistence.access import visibility_predicate
from ase.adapters.persistence.report_job_codec import with_payload
from ase.adapters.persistence.report_job_models import ReportJobRow as Row
from ase.adapters.persistence.report_origin import job_origin
from ase.domain.access import Visibility
from ase.domain.report_jobs import ReportJob, job_timestamp
from ase.domain.reports import ReportOrigin


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
    summary = (
        func.json_extract(Row.payload, "$.summary", type_=JSON)
        if session.get_bind().dialect.name == "sqlite"
        else cast(Row.payload, JSON)["summary"]
    )
    origin = job_origin(session)
    query = (
        select(Row, summary, origin)
        .options(defer(Row.payload))
        .where(visibility_predicate(Row.owner_id, Row.team_id, visibility))
    )
    if statuses is not None:
        query = query.where(Row.status.in_(tuple(statuses)))
    if not include_briefings:
        query = query.where(origin != ReportOrigin.BRIEFING.value)
    if after is not None:
        created_at, job_id = after
        job_timestamp(created_at)
        query = query.where(
            or_(Row.created_at < created_at, and_(Row.created_at == created_at, Row.id > job_id))
        )
    rows = await session.execute(
        query.order_by(Row.created_at.desc(), Row.id)
        .limit(limit)
        .execution_options(populate_existing=True)
    )
    return [
        with_payload(
            row,
            {"schema_version": 1, "summary": {**(value or {}), "origin": classified}},
        )
        for row, value, classified in rows
    ]
