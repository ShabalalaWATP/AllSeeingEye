"""Reading and editing one collection plan in place, guarded by its current revision.

A plan's revision is its `updated_at` value, which report jobs already freeze as
`collection_plan_revision`. An edit names the revision it was made from; the write is a
conditional update on that value, so two edits of one revision cannot both succeed.
Editing changes the plan for later work only. Reports and jobs keep their frozen copies.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from ase.application.access import AccessPolicy
from ase.application.auditing import Auditor
from ase.application.direction.plan_inputs import (
    PlanInput,
    plan_from_input,
    validate_plan_input,
)
from ase.application.dto import RequestContext
from ase.application.ports import Clock, UnitOfWork
from ase.application.ports.direction import AoiRepository, PlanRepository
from ase.domain.audit import AuditAction
from ase.domain.collection import CollectionPlan
from ase.domain.errors import Conflict, InvalidRequest, NotFound
from ase.domain.users import User

STALE_PLAN = (
    "This plan was changed after you opened it. Reload the latest version and reapply "
    "your edits before saving."
)


def next_revision(previous: datetime, now: datetime) -> datetime:
    """A revision strictly after the previous one, even if the clock stalls or steps back."""
    return max(now, previous + timedelta(microseconds=1))


class GetPlanUseCase:
    """The plan definition alone, without gathering live evidence."""

    def __init__(self, plans: PlanRepository, access: AccessPolicy) -> None:
        self._plans = plans
        self._access = access

    async def execute(self, actor: User, plan_id: UUID) -> CollectionPlan:
        decision = await self._access.context(actor)
        plan = await self._plans.get(plan_id)
        if plan is None:
            raise NotFound()
        decision.require_read(plan.created_by, plan.team_id)
        return plan


class UpdatePlanUseCase:
    def __init__(
        self,
        plans: PlanRepository,
        aois: AoiRepository,
        clock: Clock,
        auditor: Auditor,
        uow: UnitOfWork,
        access: AccessPolicy,
    ) -> None:
        self._plans, self._aois, self._clock = plans, aois, clock
        self._auditor, self._uow, self._access = auditor, uow, access

    async def execute(
        self,
        actor: User,
        plan_id: UUID,
        data: PlanInput,
        expected_updated_at: datetime,
        context: RequestContext,
    ) -> CollectionPlan:
        decision = await self._access.context(actor, for_update=True)
        existing = await self._plans.get(plan_id)
        if existing is None:
            raise NotFound()
        decision.require_write(existing.created_by, existing.team_id)
        if data.team_id != existing.team_id:
            raise InvalidRequest("A plan's scope cannot be changed through content editing.")
        if existing.updated_at != expected_updated_at:
            raise Conflict(STALE_PLAN)
        name, _ = await validate_plan_input(data, self._aois, decision, existing.created_by)
        now = next_revision(existing.updated_at, self._clock.now())
        plan = plan_from_input(data, name, plan_id, existing.created_by, existing.created_at, now)
        if not await self._plans.save_if_unchanged(plan, expected_updated_at):
            await self._uow.rollback()
            raise Conflict(STALE_PLAN)
        await self._auditor.record(
            AuditAction.PLAN_UPDATED, actor=actor.id, subject=str(plan_id), ip=context.ip,
            details={"pirs": len(plan.pirs), "sirs": len(plan.sirs)},
        )  # fmt: skip
        await self._uow.commit()
        return plan
