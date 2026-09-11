"""Repositories for scheduled products and the runner's own-session store."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.access import visibility_predicate
from ase.adapters.persistence.models import CollectionPlanRow, ReportRow, ScheduleRow
from ase.adapters.persistence.schedule_changes import record_change
from ase.application.access import AccessContext, AccessPolicy
from ase.domain.access import Visibility
from ase.domain.errors import Forbidden, InvalidRequest, NotFound, Unauthenticated
from ase.domain.research import ResearchFocus, ResearchMode
from ase.domain.research_changes import change_from_dict, change_to_dict
from ase.domain.schedules import Schedule


def _from_row(row: ScheduleRow) -> Schedule:
    options = row.research_options or {}
    return Schedule(
        id=row.id,
        name=row.name,
        template_id=row.template_id,
        country_iso=row.country_iso,
        plan_id=row.plan_id,
        hour_utc=row.hour_utc,
        cadence=row.cadence,
        weekday=row.weekday,
        window_hours=row.window_hours,
        enabled=row.enabled,
        created_by=row.created_by,
        created_at=row.created_at,
        next_run_at=row.next_run_at,
        last_run_at=row.last_run_at,
        last_report_id=row.last_report_id,
        last_error=row.last_error,
        team_id=row.team_id,
        notify_on_change=row.notify_on_change,
        last_change=change_from_dict(row.last_change),
        question=row.question,
        research_mode=ResearchMode(options["mode"]) if options.get("mode") else None,
        research_languages=tuple(options.get("languages") or ["en"]),
        research_focus=ResearchFocus(options.get("focus", "general")),
        research_subject=options.get("subject"),
        country_isos=tuple(options.get("country_isos", ())),
        monthday=options.get("monthday", 1),
        research_web_search=options.get("web_search", False),
        research_source_ids=tuple(options["source_ids"])
        if options.get("source_ids") is not None
        else None,
    )


def _fill(row: ScheduleRow, schedule: Schedule) -> None:
    row.name = schedule.name
    row.template_id = schedule.template_id
    row.country_iso = schedule.country_iso
    row.plan_id = schedule.plan_id
    row.hour_utc = schedule.hour_utc
    row.cadence = schedule.cadence
    row.weekday = schedule.weekday
    row.window_hours = schedule.window_hours
    row.enabled = schedule.enabled
    row.created_by = schedule.created_by
    row.created_at = schedule.created_at
    row.next_run_at = schedule.next_run_at
    row.last_run_at = schedule.last_run_at
    row.last_report_id = schedule.last_report_id
    row.last_error = schedule.last_error
    row.team_id = schedule.team_id
    row.notify_on_change = schedule.notify_on_change
    row.last_change = change_to_dict(schedule.last_change)
    row.question = schedule.question
    row.research_options = {
        "mode": schedule.research_mode.value if schedule.research_mode else None,
        "languages": list(schedule.research_languages),
        "focus": schedule.research_focus.value,
        "subject": schedule.research_subject,
        "country_isos": list(schedule.country_isos),
        "monthday": schedule.monthday,
        "web_search": schedule.research_web_search,
        "source_ids": list(schedule.research_source_ids)
        if schedule.research_source_ids is not None
        else None,
    }


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
            .where(visibility_predicate(ScheduleRow.created_by, ScheduleRow.team_id, visibility))
            .order_by(ScheduleRow.name)
        )
        return [_from_row(row) for row in rows]

    async def save(self, schedule: Schedule) -> None:
        row = await self._session.get(ScheduleRow, schedule.id)
        if row is None:
            raise NotFound("Schedule not found.")
        _fill(row, schedule)
        await self._session.flush()

    async def delete(self, schedule_id: UUID) -> None:
        await self._session.execute(delete(ScheduleRow).where(ScheduleRow.id == schedule_id))
        await self._session.flush()


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
            if not row.enabled or (row.created_by, row.team_id) != origin:
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

    async def due(self, now: datetime) -> list[Schedule]:
        async with self._session_factory() as session:
            rows = await session.scalars(
                select(ScheduleRow)
                .where(ScheduleRow.enabled.is_(True), ScheduleRow.next_run_at <= now)
                .order_by(ScheduleRow.next_run_at)
            )
            return [_from_row(row) for row in rows]

    async def mark_run(
        self,
        schedule_id: UUID,
        *,
        ran_at: datetime,
        next_run_at: datetime,
        report_id: UUID | None,
        error: str | None,
        expected: Schedule,
    ) -> None:
        async with self._session_factory() as session:
            row = await session.get(ScheduleRow, schedule_id)
            if row is None:
                return
            access = await self._authorise(session, row, for_update=True)
            if access is None or _from_row(row) != expected:
                return
            if report_id is not None:
                report = await session.get(ReportRow, report_id, populate_existing=True)
                if report is None:
                    return
                try:
                    access.require_same_scope(
                        row.created_by, row.team_id, report.created_by, report.team_id
                    )
                except (Forbidden, InvalidRequest, NotFound):
                    return
                await record_change(session, row, report, access, ran_at)
            row.last_run_at = ran_at
            row.next_run_at = next_run_at
            row.last_error = error
            if report_id is not None:
                row.last_report_id = report_id
            await session.commit()
