"""Repositories for scheduled products and the runner's own-session store."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.access import visibility_predicate
from ase.adapters.persistence.models import CollectionPlanRow, ReportRow, ScheduleRow
from ase.adapters.persistence.reports import SqlReportRepository
from ase.adapters.persistence.schedule_changes import record_change
from ase.adapters.persistence.schedule_mapping import fill_schedule_row as _fill
from ase.adapters.persistence.schedule_mapping import schedule_from_row as _from_row
from ase.adapters.persistence.subscription_briefs import load_schedule_brief
from ase.adapters.persistence.subscription_due_selection import due_schedule_rows
from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.adapters.persistence.subscription_history import remember_evidence
from ase.application.access import AccessContext, AccessPolicy
from ase.application.schedules.revision_snapshot import revision_from_schedule
from ase.application.schedules.runner import DueCursor
from ase.domain.access import Visibility
from ase.domain.errors import Conflict, Forbidden, InvalidRequest, NotFound, Unauthenticated
from ase.domain.schedules import (
    Schedule,
    ScheduleErrorCode,
    ScheduleRunResult,
)
from ase.domain.subscription_editions import SubscriptionEdition

__all__ = ["SqlScheduleRepository", "SqlScheduleStore", "_from_row", "project_edition_outcome"]


class SqlScheduleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, schedule: Schedule) -> None:
        row = ScheduleRow(id=schedule.id)
        _fill(row, schedule)
        self._session.add(row)
        await self._session.flush()

    async def get(self, schedule_id: UUID) -> Schedule | None:
        row = await self._session.get(ScheduleRow, schedule_id, populate_existing=True)
        return None if row is None else _from_row(row)

    async def list_all(self, visibility: Visibility) -> list[Schedule]:
        rows = await self._session.scalars(
            select(ScheduleRow)
            .where(
                visibility_predicate(ScheduleRow.created_by, ScheduleRow.team_id, visibility),
                ScheduleRow.archived_at.is_(None),
            )
            .order_by(ScheduleRow.name)
        )
        return [_from_row(row) for row in rows]

    async def save(self, schedule: Schedule) -> None:
        row = await self._session.get(ScheduleRow, schedule.id)
        if row is None:
            raise NotFound("Schedule not found.")
        if row.archived_at is not None or schedule.archived_at is not None:
            raise NotFound("Schedule not found.")
        _fill(row, schedule)
        await self._session.flush()

    async def archive(self, schedule: Schedule, archived_at: datetime) -> bool:
        """Keep the FK parent and immutable children; one atomic tombstone write wins."""
        result = await self._session.scalar(
            update(ScheduleRow)
            .where(
                ScheduleRow.id == schedule.id,
                ScheduleRow.created_by == schedule.created_by,
                ScheduleRow.team_id == schedule.team_id,
                ScheduleRow.archived_at.is_(None),
            )
            .values(enabled=False, archived_at=archived_at)
            .returning(ScheduleRow.id)
        )
        return result is not None


class SqlScheduleStore:
    """Opens its own session per call, so the runner never shares one with a request."""

    def __init__(
        self,
        session_factory: Callable[[], AsyncSession],
        policy_factory: Callable[[AsyncSession], AccessPolicy],
    ) -> None:
        self._session_factory = session_factory
        self._policy_factory = policy_factory

    async def _authorise(
        self, session: AsyncSession, row: ScheduleRow, *, for_update: bool = False
    ) -> AccessContext | None:
        origin = (row.created_by, row.team_id)
        try:
            access = await self._policy_factory(session).background(
                row.created_by, row.team_id, for_update=for_update
            )
            current = await session.get(ScheduleRow, row.id, populate_existing=True)
            if current is None:
                return None
            if (
                not row.enabled
                or row.archived_at is not None
                or (row.created_by, row.team_id) != origin
            ):
                return None
            if row.plan_id is not None:
                plan = await session.get(CollectionPlanRow, row.plan_id, populate_existing=True)
                if plan is None:
                    return None
                access.require_same_scope(
                    row.created_by, row.team_id, plan.created_by, plan.team_id
                )
            return access
        except (Forbidden, InvalidRequest, NotFound, Unauthenticated):
            return None

    async def can_run(self, schedule: Schedule) -> bool:
        async with self._session_factory() as session:
            row = await session.get(ScheduleRow, schedule.id)
            if row is None or await self._authorise(session, row) is None:
                return False
            return _from_row(row) == schedule

    async def due(self, now: datetime, *, limit: int = 16) -> list[Schedule]:
        items, _ = await self.due_batch(now, limit=limit)
        return items

    async def due_batch(
        self, now: datetime, *, limit: int = 16, cursor: DueCursor | None = None
    ) -> tuple[list[Schedule], DueCursor | None]:
        async with self._session_factory() as session:
            rows, next_cursor = await due_schedule_rows(session, now, limit=limit, cursor=cursor)
            return [_from_row(row) for row in rows], next_cursor

    async def mark_run(
        self,
        schedule_id: UUID,
        *,
        ran_at: datetime,
        next_run_at: datetime,
        result: ScheduleRunResult | None,
        error_code: ScheduleErrorCode | None,
        expected: Schedule,
    ) -> None:
        async with self._session_factory() as session:
            row = await session.get(ScheduleRow, schedule_id)
            if row is None:
                return
            access = await self._authorise(session, row, for_update=True)
            if access is None or _from_row(row) != expected:
                return
            if result is not None:
                report = await session.get(ReportRow, result.report_id, populate_existing=True)
                if report is None:
                    return
                try:
                    access.require_same_scope(
                        row.created_by, row.team_id, report.created_by, report.team_id
                    )
                except (Forbidden, InvalidRequest, NotFound):
                    return
                version = await SqlReportRepository(session).get_version(report.id, 1)
                if (
                    version is None
                    or ScheduleRunResult.from_version(
                        version, research_required=expected.research_mode is not None
                    )
                    != result
                ):
                    return
                if result.successful:
                    await record_change(session, row, report, access, ran_at)
                    await remember_evidence(session, row, report)
            row.last_run_at = ran_at
            row.next_run_at = next_run_at
            row.last_error = (result.error_code if result else error_code) or None
            options = dict(row.research_options or {})
            options["last_version_id"] = str(result.version_id) if result else None
            options["last_outcome"] = result.outcome.value if result else None
            options["last_coverage"] = result.coverage.value if result else None
            row.research_options = options
            if result is not None:
                row.last_report_id = result.report_id
            await session.commit()


async def project_edition_outcome(
    session: AsyncSession,
    edition: SubscriptionEdition,
    result: ScheduleRunResult,
    access: AccessContext,
) -> bool:
    """Project a published edition in the caller's report transaction.

    A changed subscription may still retain its historical edition, but must not
    have its current comparison state overwritten by an older execution.
    """
    row = await session.get(ScheduleRow, edition.subscription_id, populate_existing=True)
    if row is None or not row.enabled or row.archived_at is not None:
        return False
    schedule = _from_row(row)
    frozen = await SqlSubscriptionEditionRepository(session).get_revision(
        edition.subscription_id, edition.frozen_revision
    )
    brief = await load_schedule_brief(session, access, schedule)
    if (
        frozen is None
        or (schedule.created_by, schedule.team_id) != (frozen.owner_id, frozen.team_id)
        or revision_from_schedule(schedule, 1, brief=brief).compatibility_fingerprint
        != edition.compatibility_fingerprint
    ):
        return False
    report = await session.get(ReportRow, result.report_id, populate_existing=True)
    if report is None:
        raise Conflict("The published subscription report is unavailable.")
    access.require_same_scope(row.created_by, row.team_id, report.created_by, report.team_id)
    version = await SqlReportRepository(session).get_version(report.id, 1)
    if (
        version is None
        or ScheduleRunResult.from_version(
            version, research_required=schedule.research_mode is not None
        )
        != result
    ):
        raise Conflict("The published subscription version does not match its edition.")
    if result.successful:
        await record_change(session, row, report, access, edition.updated_at)
        await remember_evidence(session, row, report)
    row.last_report_id = result.report_id
    row.last_run_at = edition.updated_at
    row.last_error = result.error_code.value if result.error_code else None
    options = dict(row.research_options or {})
    options.update(
        last_version_id=str(result.version_id),
        last_outcome=result.outcome.value,
        last_coverage=result.coverage.value,
    )
    row.research_options = options
    await session.flush()
    return True
