"""Personal and team schedules governed by current membership and write authority."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from ase.application.access import AccessContext, AccessPolicy
from ase.application.auditing import Auditor
from ase.application.dto import RequestContext
from ase.application.ports import Clock, UnitOfWork
from ase.application.ports.direction import PlanRepository
from ase.application.ports.schedules import ScheduleRepository
from ase.application.reports.templates import TEMPLATES
from ase.domain.audit import AuditAction
from ase.domain.errors import InvalidRequest, NotFound
from ase.domain.research import ResearchFocus, ResearchMode
from ase.domain.schedules import CADENCES, Schedule, next_run_after
from ase.domain.users import User

MAX_WINDOW_HOURS = 336


@dataclass(frozen=True, slots=True)
class ScheduleInput:
    name: str
    template_id: str
    country_iso: str | None = None
    plan_id: UUID | None = None
    hour_utc: int = 6
    cadence: str = "daily"
    weekday: int = 0
    window_hours: int | None = None
    enabled: bool = True
    team_id: UUID | None = None
    notify_on_change: bool = False
    question: str | None = None
    research_mode: ResearchMode | None = None
    research_languages: tuple[str, ...] = ("en",)
    research_focus: ResearchFocus = ResearchFocus.GENERAL
    research_subject: str | None = None


def _research_question(data: ScheduleInput) -> str | None:
    if data.research_focus in (ResearchFocus.DOCUMENT, ResearchFocus.MEDIA):
        raise InvalidRequest(
            "Document and media inputs expire and cannot be scheduled. "
            "Use an interactive follow-up on the saved report instead."
        )
    question = data.question.strip() if data.question else None
    if question is not None and not 1 <= len(question) <= 1000:
        raise InvalidRequest("A question needs between 1 and 1000 characters.")
    if data.research_mode is not None and not question:
        raise InvalidRequest("On-demand research requires a saved question.")
    if data.research_mode is not None and data.research_mode not in ResearchMode:
        raise InvalidRequest("Unknown research mode.")
    if data.research_mode and data.research_focus != ResearchFocus.GENERAL and data.country_iso:
        raise InvalidRequest("Focused research uses its subject scope, not a nation filter.")
    if data.research_focus not in ResearchFocus:
        raise InvalidRequest("Unknown research focus.")
    if not 1 <= len(data.research_languages) <= 8 or any(
        re.fullmatch(r"[a-z]{2,3}(-[a-z]{2,4})?", code.lower()) is None
        for code in data.research_languages
    ):
        raise InvalidRequest("Provide between one and eight language codes.")
    if data.research_subject is not None and len(data.research_subject) > 300:
        raise InvalidRequest("The research subject must not exceed 300 characters.")
    return question


def build_schedule(
    data: ScheduleInput,
    *,
    schedule_id: UUID,
    owner: UUID,
    created: datetime,
    now: datetime,
    previous: Schedule | None = None,
) -> Schedule:
    name = " ".join(data.name.split())
    if not name:
        raise InvalidRequest("A schedule needs a name.")
    template = TEMPLATES.get(data.template_id)
    if template is None:
        raise InvalidRequest("Unknown report template.")
    if template.needs_conflict or template.needs_hazard:
        raise InvalidRequest("This product cannot be scheduled yet.")
    question = _research_question(data)
    if template.needs_question and data.plan_id is None and not question:
        raise InvalidRequest("Ask the Eye needs a question or collection plan.")
    country = data.country_iso.strip().upper() if data.country_iso else None
    if country is not None and len(country) != 2:
        raise InvalidRequest("A nation is a two-letter ISO code.")
    if template.needs_country and country is None:
        raise InvalidRequest("This product needs a nation.")
    if not (0 <= data.hour_utc <= 23):
        raise InvalidRequest("The hour must be between 0 and 23 UTC.")
    if data.cadence not in CADENCES:
        raise InvalidRequest("The cadence is daily, weekdays or weekly.")
    if not (0 <= data.weekday <= 6):
        raise InvalidRequest("The weekday must be between 0 (Monday) and 6 (Sunday).")
    if data.window_hours is not None and not (1 <= data.window_hours <= MAX_WINDOW_HOURS):
        raise InvalidRequest("The window must be between 1 and 336 hours.")
    if data.notify_on_change and not question and data.plan_id is None:
        raise InvalidRequest("Change monitoring requires a saved question or collection plan.")
    reset = previous is None or any(
        getattr(previous, key) != getattr(data, key)
        for key in (
            "question",
            "research_mode",
            "research_languages",
            "research_focus",
            "research_subject",
            "country_iso",
            "plan_id",
            "window_hours",
            "template_id",
            "notify_on_change",
        )
    )
    return Schedule(
        id=schedule_id,
        name=name[:120],
        template_id=template.id,
        country_iso=country,
        plan_id=data.plan_id,
        hour_utc=data.hour_utc,
        cadence=data.cadence,
        weekday=data.weekday,
        window_hours=data.window_hours,
        enabled=data.enabled,
        created_by=owner,
        created_at=created,
        next_run_at=next_run_after(now, data.hour_utc, data.cadence, data.weekday),
        last_run_at=None if previous is None else previous.last_run_at,
        last_report_id=None if previous is None else previous.last_report_id,
        last_error=None if previous is None else previous.last_error,
        team_id=data.team_id,
        notify_on_change=data.notify_on_change,
        last_change=None if reset or previous is None else previous.last_change,
        question=question,
        research_mode=data.research_mode,
        research_languages=tuple(dict.fromkeys(code.lower() for code in data.research_languages)),
        research_focus=data.research_focus,
        research_subject=data.research_subject.strip() or None if data.research_subject else None,
    )


class _ScheduleUseCase:
    def __init__(
        self,
        schedules: ScheduleRepository,
        plans: PlanRepository,
        clock: Clock,
        auditor: Auditor,
        uow: UnitOfWork,
        access: AccessPolicy,
    ) -> None:
        self._schedules = schedules
        self._plans = plans
        self._clock = clock
        self._auditor = auditor
        self._uow = uow
        self._access = access

    async def _check_plan(self, data: ScheduleInput, owner: UUID, access: AccessContext) -> None:
        if data.plan_id is None:
            return
        plan = await self._plans.get(data.plan_id)
        if plan is None:
            raise InvalidRequest("Unknown collection plan.")
        access.require_same_scope(owner, data.team_id, plan.created_by, plan.team_id)

    async def _existing(self, actor: User, schedule_id: UUID) -> Schedule:
        access = await self._access.context(actor, for_update=True)
        schedule = await self._schedules.get(schedule_id)
        if schedule is None:
            raise NotFound("Schedule not found.")
        access.require_write(schedule.created_by, schedule.team_id)
        return schedule


class CreateScheduleUseCase(_ScheduleUseCase):
    async def execute(self, actor: User, data: ScheduleInput, context: RequestContext) -> Schedule:
        access = await self._access.context(actor, for_update=True)
        access.require_create(data.team_id)
        await self._check_plan(data, actor.id, access)
        now = self._clock.now()
        schedule = build_schedule(data, schedule_id=uuid4(), owner=actor.id, created=now, now=now)
        await self._schedules.add(schedule)
        await self._auditor.record(
            AuditAction.SCHEDULE_CREATED, actor=actor.id, subject=str(schedule.id),
            ip=context.ip, details={"name": schedule.name, "template": schedule.template_id},
        )  # fmt: skip
        await self._uow.commit()
        return schedule


class UpdateScheduleUseCase(_ScheduleUseCase):
    async def execute(
        self, actor: User, schedule_id: UUID, data: ScheduleInput, context: RequestContext
    ) -> Schedule:
        existing = await self._existing(actor, schedule_id)
        if data.team_id != existing.team_id:
            raise InvalidRequest("A schedule's personal or team scope cannot be changed.")
        access = await self._access.context(actor)
        await self._check_plan(data, existing.created_by, access)
        schedule = build_schedule(
            data, schedule_id=existing.id, owner=existing.created_by,
            created=existing.created_at, now=self._clock.now(), previous=existing,
        )  # fmt: skip
        await self._schedules.save(schedule)
        await self._auditor.record(
            AuditAction.SCHEDULE_UPDATED, actor=actor.id, subject=str(schedule.id),
            ip=context.ip, details={"name": schedule.name, "enabled": schedule.enabled},
        )  # fmt: skip
        await self._uow.commit()
        return schedule


class DeleteScheduleUseCase(_ScheduleUseCase):
    async def execute(self, actor: User, schedule_id: UUID, context: RequestContext) -> None:
        schedule = await self._existing(actor, schedule_id)
        await self._schedules.delete(schedule.id)
        await self._auditor.record(
            AuditAction.SCHEDULE_DELETED, actor=actor.id, subject=str(schedule.id),
            ip=context.ip, details={"name": schedule.name},
        )  # fmt: skip
        await self._uow.commit()


class ListSchedulesUseCase:
    def __init__(self, schedules: ScheduleRepository, access: AccessPolicy) -> None:
        self._schedules = schedules
        self._access = access

    async def execute(self, actor: User) -> list[Schedule]:
        access = await self._access.context(actor)
        return await self._schedules.list_all(access.visibility)
