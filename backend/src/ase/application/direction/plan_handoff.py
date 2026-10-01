"""Checks that a plan-led brief still names the plan revision its author reviewed.

The research form shows the plan's requirements before submission and sends back the
revision (`updated_at`) it showed. Submission is refused when that plan is missing,
unreadable, disabled, in another workspace or changed since. The job then freezes the
revision it used, so later edits stop queued work rather than changing its scope.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from ase.application.access import AccessPolicy
from ase.application.ports.direction import PlanRepository
from ase.domain.collection import CollectionPlan
from ase.domain.errors import Conflict, InvalidRequest, NotFound
from ase.domain.users import User

UNAVAILABLE = (
    "This collection plan no longer exists or is not available to you. Remove it from "
    "the brief or open the assessment again from a plan you can read."
)


class RequireReviewedPlan:
    def __init__(self, plans: PlanRepository, access: AccessPolicy) -> None:
        self._plans = plans
        self._access = access

    async def execute(
        self,
        actor: User,
        plan_id: UUID,
        team_id: UUID | None,
        expected_updated_at: datetime | None,
    ) -> CollectionPlan:
        decision = await self._access.context(actor)
        plan = await self._plans.get(plan_id)
        if plan is None:
            raise NotFound(UNAVAILABLE)
        decision.require_read(plan.created_by, plan.team_id)
        if plan.team_id != team_id:
            raise InvalidRequest(
                "This brief and its collection plan belong to different workspaces. "
                "Start the assessment again from the plan."
            )
        if not plan.enabled:
            raise InvalidRequest(
                "This collection plan is disabled. Enable it in Plans and areas before "
                "starting research from it."
            )
        if expected_updated_at is None:
            raise InvalidRequest(
                "Review the collection plan's current requirements before starting research."
            )
        if plan.updated_at != expected_updated_at:
            raise Conflict(
                "The collection plan changed after you reviewed it. Reload its requirements, "
                "check the brief, then start the research again."
            )
        return plan
