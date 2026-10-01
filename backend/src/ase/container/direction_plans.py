"""Composition of collection-plan reads, map matching and research hand-off checks.

Plan creation, editing, listing, deletion and evidence remain in `features.py`.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from ase.application.direction.plan_handoff import RequireReviewedPlan
from ase.application.direction.plan_map_matches import PlanMapMatchesUseCase
from ase.application.direction.plan_updates import GetPlanUseCase
from ase.application.direction.plans import PlanEvidenceUseCase
from ase.container.core import ContainerCore


class DirectionPlanWiring(ContainerCore):
    def plan_definition(self, session: AsyncSession) -> GetPlanUseCase:
        return GetPlanUseCase(self.repositories(session).plans, self.access_policy(session))

    def plan_handoff(self, session: AsyncSession) -> RequireReviewedPlan:
        return RequireReviewedPlan(self.repositories(session).plans, self.access_policy(session))

    def plan_map_matches(self, session: AsyncSession) -> PlanMapMatchesUseCase:
        r = self.repositories(session)
        return PlanMapMatchesUseCase(
            PlanEvidenceUseCase(
                r.plans, r.aois, self.store, self.clock, self.access_policy(session)
            )
        )
