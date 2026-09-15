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
from ase.adapters.persistence.subscription_briefs import load_schedule_brief
from ase.adapters.persistence.subscription_due_selection import due_schedule_rows
from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.adapters.persistence.subscription_history import remember_evidence
from ase.application.access import AccessContext, AccessPolicy
from ase.application.schedules.revision_snapshot import revision_from_schedule
from ase.application.schedules.runner import DueCursor
from ase.domain.access import Visibility
from ase.domain.errors import Conflict, Forbidden, InvalidRequest, NotFound, Unauthenticated
from ase.domain.reports import ReportStatus
from ase.domain.research import ResearchFocus, ResearchMode
from ase.domain.research_area import area_from_dict, area_to_dict
from ase.domain.research_changes import change_from_dict, change_to_dict
from ase.domain.schedules import (
    CoverageState,
    Schedule,
    ScheduleErrorCode,
    ScheduleRunResult,
)
from ase.domain.subscription_editions import SubscriptionEdition
from ase.domain.subscription_recurrence import WindowPolicy


def _from_row(row: ScheduleRow) -> Schedule:
    options = row.research_options or {}
    return Schedule(
        id=row.id,
        name=row.name,
        template_id=row.template_id,
        country_iso=row.country_iso,
        plan_id=row.plan_id,
        hour_utc=row.hour_utc,
        timezone=row.timezone,
        local_hour=row.local_hour,
        local_minute=row.local_minute,
        collection_policy=WindowPolicy(row.collection_policy),
        brief_id=row.brief_id,
        brief_revision=row.brief_revision,
        cadence=row.cadence,
        weekday=row.weekday,
        window_hours=row.window_hours,
        enabled=row.enabled,
        archived_at=row.archived_at,
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
        anchor_month=options.get("anchor_month", 1),
        conflict_id=options.get("conflict_id"),
        hazard=options.get("hazard"),
        research_area=area_from_dict(options.get("research_area")),
        disclose_area_to_provider=options.get("disclose_area_to_provider", False),
        avoid_repetition=options.get("avoid_repetition", True),
        seen_content_signatures=tuple(options.get("seen_content_signatures", ()))[:500],
        baseline_report_id=UUID(options["baseline_report_id"])
        if options.get("baseline_report_id")
        else None,
        last_version_id=UUID(options["last_version_id"])
        if options.get("last_version_id")
        else None,
        last_outcome=ReportStatus(options["last_outcome"]) if options.get("last_outcome") else None,
        last_coverage=CoverageState(options["last_coverage"])
        if options.get("last_coverage")
        else CoverageState.UNKNOWN
        if "last_coverage" not in options and (row.last_run_at or row.last_report_id)
        else None,
    )


def _fill(row: ScheduleRow, schedule: Schedule) -> None:
    row.name = schedule.name
    row.template_id = schedule.template_id
    row.country_iso = schedule.country_iso
    row.plan_id = schedule.plan_id
    row.hour_utc = schedule.hour_utc
    row.timezone = schedule.timezone
    row.local_hour = schedule.local_hour if schedule.local_hour is not None else schedule.hour_utc
    row.local_minute = schedule.local_minute
    row.collection_policy = schedule.collection_policy.value
    row.brief_id = schedule.brief_id
    row.brief_revision = schedule.brief_revision
    row.cadence = schedule.cadence
    row.weekday = schedule.weekday
    row.window_hours = schedule.window_hours
    row.enabled = schedule.enabled
    row.archived_at = schedule.archived_at
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
        "anchor_month": schedule.anchor_month,
        "conflict_id": schedule.conflict_id,
        "hazard": schedule.hazard,
        "research_area": area_to_dict(schedule.research_area),
        "disclose_area_to_provider": schedule.disclose_area_to_provider,
        "avoid_repetition": schedule.avoid_repetition,
        "seen_content_signatures": list(schedule.seen_content_signatures),
        "baseline_report_id": str(schedule.baseline_report_id)
        if schedule.baseline_report_id
        else None,
        "last_version_id": str(schedule.last_version_id) if schedule.last_version_id else None,
        "last_outcome": schedule.last_outcome.value if schedule.last_outcome else None,
        "last_coverage": schedule.last_coverage.value if schedule.last_coverage else None,
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
