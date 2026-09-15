"""Personal and team schedules governed by current membership and write authority."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import replace
from uuid import UUID, uuid4

from ase.application.access import AccessContext, AccessPolicy
from ase.application.auditing import Auditor
from ase.application.dto import RequestContext
from ase.application.ports import Clock, UnitOfWork
from ase.application.ports.direction import PlanRepository
from ase.application.ports.schedules import ScheduleRepository
from ase.application.ports.trackers import ConflictDirectory
from ase.application.schedules.definition import ScheduleInput, build_schedule
from ase.application.schedules.edition_planning import rebased_next_run
from ase.domain.audit import AuditAction
from ase.domain.errors import InvalidRequest, NotFound
from ase.domain.schedules import Schedule
from ase.domain.users import User


class _ScheduleUseCase:
    def __init__(
        self,
        schedules: ScheduleRepository,
        plans: PlanRepository,
        clock: Clock,
        auditor: Auditor,
        uow: UnitOfWork,
        access: AccessPolicy,
        conflicts: ConflictDirectory | None = None,
    ) -> None:
        self._schedules = schedules
        self._plans = plans
        self._clock = clock
        self._auditor = auditor
        self._uow = uow
        self._access = access
        self._conflicts = conflicts

    async def _check_plan(self, data: ScheduleInput, owner: UUID, access: AccessContext) -> None:
        if data.conflict_id is not None and (
            self._conflicts is None or self._conflicts.get(data.conflict_id) is None
        ):
            raise InvalidRequest("Choose a conflict from the tracker list.")
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
        if schedule.archived_at is not None:
            raise NotFound("Schedule not found.")
        return schedule


class CreateScheduleUseCase(_ScheduleUseCase):
    async def execute(
        self,
        actor: User,
        data: ScheduleInput,
        context: RequestContext,
        *,
        check_session: Callable[[], Awaitable[None]] | None = None,
    ) -> Schedule:
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
        if check_session is not None:
            await check_session()
        await self._uow.commit()
        return schedule


class UpdateScheduleUseCase(_ScheduleUseCase):
    async def execute(
        self,
        actor: User,
        schedule_id: UUID,
        data: ScheduleInput,
        context: RequestContext,
        *,
        check_session: Callable[[], Awaitable[None]] | None = None,
    ) -> Schedule:
        existing = await self._existing(actor, schedule_id)
        if existing.brief_id is not None:
            raise InvalidRequest(
                "A brief-linked subscription needs a dedicated revision-safe edit action."
            )
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
        if check_session is not None:
            await check_session()
        await self._uow.commit()
        return schedule


class DeleteScheduleUseCase(_ScheduleUseCase):
    async def stage(
        self,
        actor: User,
        schedule_id: UUID,
        context: RequestContext,
    ) -> tuple[Schedule, bool]:
        access = await self._access.context(actor, for_update=True)
        schedule = await self._schedules.get(schedule_id)
        if schedule is None:
            raise NotFound("Schedule not found.")
        access.require_write(schedule.created_by, schedule.team_id)
        if schedule.archived_at is not None:
            return schedule, False
        archived_at = self._clock.now()
        if not await self._schedules.archive(schedule, archived_at):
            raise NotFound("Schedule not found.")
        await self._auditor.record(
            AuditAction.SCHEDULE_DELETED, actor=actor.id, subject=str(schedule.id),
            ip=context.ip, details={"name": schedule.name, "archived": True},
        )  # fmt: skip
        return replace(schedule, enabled=False, archived_at=archived_at), True


class ListSchedulesUseCase:
    def __init__(self, schedules: ScheduleRepository, access: AccessPolicy) -> None:
        self._schedules = schedules
        self._access = access

    async def execute(self, actor: User) -> list[Schedule]:
        access = await self._access.context(actor)
        return await self._schedules.list_all(access.visibility)


class SetScheduleEnabledUseCase:
    """Stage only the activation flag; the caller commits alongside retained work."""

    def __init__(
        self, schedules: ScheduleRepository, access: AccessPolicy, auditor: Auditor, clock: Clock
    ) -> None:
        self._schedules = schedules
        self._access = access
        self._auditor = auditor
        self._clock = clock

    async def stage(
        self,
        actor: User,
        schedule_id: UUID,
        enabled: bool,
        context: RequestContext,
    ) -> tuple[Schedule, bool]:
        access = await self._access.context(actor, for_update=True)
        existing = await self._schedules.get(schedule_id)
        if existing is None:
            raise NotFound("Subscription not found.")
        access.require_write(existing.created_by, existing.team_id)
        if existing.archived_at is not None:
            raise NotFound("Subscription not found.")
        if existing.enabled is enabled:
            return existing, False
        updated = replace(existing, enabled=enabled)
        rebased = rebased_next_run(existing, self._clock.now()) if enabled else None
        if rebased is not None:
            # A long pause cannot be caught up automatically; resume at the latest slot.
            updated = replace(updated, next_run_at=rebased)
        await self._schedules.save(updated)
        await self._auditor.record(
            AuditAction.SCHEDULE_UPDATED,
            actor=actor.id,
            subject=str(schedule_id),
            ip=context.ip,
            details={"name": existing.name, "action": "resume" if enabled else "pause"},
        )
        return updated, True
