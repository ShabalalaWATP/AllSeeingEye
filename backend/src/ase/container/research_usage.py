"""Session-scoped research allowance policy, readiness and persistence wiring."""

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.research_usage import SqlResearchUsageRepository
from ase.adapters.persistence.teams import SqlTeamRepository
from ase.application.research_readiness import ResearchReadiness
from ase.application.research_usage import ResearchUsageService
from ase.container.core import ContainerCore


class ResearchUsageWiring(ContainerCore):
    def research_usage(self, session: AsyncSession) -> ResearchUsageService:
        repos = self.repositories(session)
        return ResearchUsageService(
            SqlResearchUsageRepository(session),
            repos.users,
            self.access_policy(session),
            self.clock,
            repos.uow,
            self._auditor(repos),
        )

    def research_readiness(self, session: AsyncSession) -> ResearchReadiness:
        repos = self.repositories(session)
        return ResearchReadiness(repos.llm_profiles, repos.llm_bindings, SqlTeamRepository(session))
