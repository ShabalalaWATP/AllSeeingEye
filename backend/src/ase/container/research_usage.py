"""Session-scoped research allowance policy and persistence wiring."""

from typing import TYPE_CHECKING, cast

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.research_usage import SqlResearchUsageRepository
from ase.application.research_usage import ResearchUsageService

if TYPE_CHECKING:
    from ase.container import Container


class ResearchUsageWiring:
    def research_usage(self, session: AsyncSession) -> ResearchUsageService:
        container = cast("Container", self)
        repos = container.repositories(session)
        return ResearchUsageService(
            SqlResearchUsageRepository(session),
            repos.users,
            container.access_policy(session),
            container.clock,
            repos.uow,
            container._auditor(repos),
        )
