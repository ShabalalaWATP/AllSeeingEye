"""Linked-record checks for live views.

A view may name one collection plan filter. The plan must be readable now and share the
view's personal owner or team, even for administrators. Runs inside the caller's locked
transaction.
"""

from typing import Any
from uuid import UUID

from ase.application.access import AccessContext
from ase.application.ports.direction import PlanRepository
from ase.domain.errors import NotFound
from ase.domain.live_views import view_plan
from ase.domain.map_workspace import WorkspaceKind


class MapWorkspaceLinks:
    def __init__(self, plans: PlanRepository) -> None:
        self.plans = plans

    async def check(
        self,
        access: AccessContext,
        kind: WorkspaceKind,
        payload: dict[str, Any],
        created_by: UUID,
        team_id: UUID | None,
    ) -> None:
        if kind != "live_view":
            return
        plan_id = view_plan(payload)
        if plan_id is not None:
            plan = await self.plans.get(plan_id)
            if plan is None:
                raise NotFound()
            access.require_same_scope(created_by, team_id, plan.created_by, plan.team_id)
