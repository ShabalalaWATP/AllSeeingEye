"""Composition of collection-plan reads, map matching and research hand-off checks.

Plan creation, editing, listing, deletion and evidence remain in `features.py`.
"""

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from ase.application.direction.plan_handoff import RequireReviewedPlan
from ase.application.direction.plan_updates import GetPlanUseCase
from ase.container.core import ContainerCore

if TYPE_CHECKING:
    pass


class DirectionPlanWiring(ContainerCore):
    def plan_definition(self, session: AsyncSession) -> GetPlanUseCase:
        return GetPlanUseCase(self.repositories(session).plans, self.access_policy(session))

    def plan_handoff(self, session: AsyncSession) -> RequireReviewedPlan:
        return RequireReviewedPlan(self.repositories(session).plans, self.access_policy(session))
