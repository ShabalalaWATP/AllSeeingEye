"""Collect explicit private roots, never treating a baseline reference as ownership."""

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute, defer

from ase.adapters.persistence.base import Base
from ase.adapters.persistence.models import ReportRow, ScheduleRow
from ase.adapters.persistence.report_job_models import ReportJobRow
from ase.adapters.persistence.research_brief_models import ResearchBriefRevisionRow
from ase.adapters.persistence.subscription_edition_models import (
    SubscriptionAttemptRow,
    SubscriptionEditionRow,
)
from ase.domain.errors import NotFound
from ase.domain.private_removal import RemovalRequest, RemovalScope

MAX_ROOTS = 250


def _lightweight(query: Any, model: type[Base]) -> Any:
    if model in (ReportJobRow, ResearchBriefRevisionRow):
        return query.options(defer(model.payload))
    return query


@dataclass
class RemovalGraph:
    reports: list[ReportRow] = field(default_factory=list)
    schedules: list[ScheduleRow] = field(default_factory=list)
    jobs: list[ReportJobRow] = field(default_factory=list)
    briefs: list[ResearchBriefRevisionRow] = field(default_factory=list)
    blockers: set[str] = field(default_factory=set)

    @property
    def report_ids(self) -> set[UUID]:
        return {row.id for row in self.reports}

    @property
    def schedule_ids(self) -> set[UUID]:
        return {row.id for row in self.schedules}

    @property
    def job_ids(self) -> set[UUID]:
        return {row.id for row in self.jobs}

    @property
    def brief_ids(self) -> set[UUID]:
        return {row.brief_id for row in self.briefs}


async def _roots[T: Base](
    session: AsyncSession,
    model: type[T],
    key: InstrumentedAttribute[Any],
    owner: InstrumentedAttribute[Any],
    request: RemovalRequest,
    scope: RemovalScope,
) -> list[T]:
    if request.scope not in (RemovalScope.ACCOUNT, scope):
        return []
    query = select(model).where(owner == request.owner_id, model.team_id.is_(None))  # type: ignore[attr-defined]
    if request.scope is not RemovalScope.ACCOUNT:
        query = query.where(key == request.target_id)
    rows = list(
        await session.scalars(_lightweight(query, model).order_by(key).limit(MAX_ROOTS + 1))
    )
    if request.scope is scope and not rows:
        raise NotFound()
    return rows


async def collect_graph(session: AsyncSession, request: RemovalRequest) -> RemovalGraph:
    graph = RemovalGraph(
        reports=await _roots(
            session, ReportRow, ReportRow.id, ReportRow.created_by, request, RemovalScope.REPORT
        ),
        schedules=await _roots(
            session,
            ScheduleRow,
            ScheduleRow.id,
            ScheduleRow.created_by,
            request,
            RemovalScope.SUBSCRIPTION,
        ),
        jobs=await _roots(
            session, ReportJobRow, ReportJobRow.id, ReportJobRow.owner_id, request, RemovalScope.JOB
        ),
        briefs=await _roots(
            session,
            ResearchBriefRevisionRow,
            ResearchBriefRevisionRow.brief_id,
            ResearchBriefRevisionRow.owner_id,
            request,
            RemovalScope.BRIEF,
        ),
    )
    if request.scope is RemovalScope.BRIEF:
        graph.schedules = list(
            await session.scalars(
                select(ScheduleRow)
                .where(
                    ScheduleRow.brief_id.in_(graph.brief_ids),
                    ScheduleRow.created_by == request.owner_id,
                    ScheduleRow.team_id.is_(None),
                )
                .limit(MAX_ROOTS + 1)
            )
        )
        graph.jobs = list(
            await session.scalars(
                select(ReportJobRow)
                .options(defer(ReportJobRow.payload))
                .where(
                    ReportJobRow.brief_id.in_(graph.brief_ids),
                    ReportJobRow.owner_id == request.owner_id,
                    ReportJobRow.team_id.is_(None),
                )
                .limit(MAX_ROOTS + 1)
            )
        )
    linked_jobs = set(
        await session.scalars(
            select(SubscriptionEditionRow.job_id)
            .where(
                SubscriptionEditionRow.subscription_id.in_(graph.schedule_ids),
                SubscriptionEditionRow.job_id.is_not(None),
            )
            .distinct()
            .limit(MAX_ROOTS + 1)
        )
    )
    editions = select(SubscriptionEditionRow.id).where(
        SubscriptionEditionRow.subscription_id.in_(graph.schedule_ids)
    )
    linked_jobs.update(
        await session.scalars(
            select(SubscriptionAttemptRow.job_id)
            .where(
                SubscriptionAttemptRow.edition_id.in_(editions),
                SubscriptionAttemptRow.job_id.is_not(None),
            )
            .distinct()
            .limit(MAX_ROOTS + 1)
        )
    )
    # A report's retained checkpoint contains selected private inputs independently.
    related = list(
        await session.scalars(
            select(ReportJobRow)
            .options(defer(ReportJobRow.payload))
            .where(ReportJobRow.id.in_(linked_jobs) | ReportJobRow.report_id.in_(graph.report_ids))
            .limit(MAX_ROOTS + 1)
        )
    )
    if any(row.owner_id != request.owner_id or row.team_id is not None for row in related):
        graph.blockers.add("shared_or_foreign_job_dependency")
    graph.jobs = list(
        {
            row.id: row
            for row in [*graph.jobs, *related]
            if row.owner_id == request.owner_id and row.team_id is None
        }.values()
    )
    produced = set(
        await session.scalars(
            select(SubscriptionEditionRow.report_id)
            .where(
                SubscriptionEditionRow.subscription_id.in_(graph.schedule_ids),
                SubscriptionEditionRow.report_id.is_not(None),
            )
            .distinct()
            .limit(MAX_ROOTS + 1)
        )
    )
    if request.scope in (RemovalScope.ACCOUNT, RemovalScope.SUBSCRIPTION, RemovalScope.BRIEF):
        produced.update(row.report_id for row in graph.jobs)
    reports = list(
        await session.scalars(
            select(ReportRow).where(ReportRow.id.in_(produced)).limit(MAX_ROOTS + 1)
        )
    )
    if any(row.created_by != request.owner_id or row.team_id is not None for row in reports):
        graph.blockers.add("shared_or_foreign_report_dependency")
    graph.reports = list(
        {
            row.id: row
            for row in [*graph.reports, *reports]
            if row.created_by == request.owner_id and row.team_id is None
        }.values()
    )
    if any(
        len(rows) > MAX_ROOTS for rows in (graph.reports, graph.schedules, graph.jobs, graph.briefs)
    ):
        graph.blockers.add("graph_limit_use_individual_saved_work_scopes")
    if any(len(rows) > MAX_ROOTS for rows in (linked_jobs, produced, related, reports)):
        graph.blockers.add("graph_limit_use_individual_saved_work_scopes")
    return graph
