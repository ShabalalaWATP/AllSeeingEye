"""Session-local administrator research-quality scorecard; read only, nothing persisted."""

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.research_quality import SqlResearchQualityReader
from ase.application.admin.research_quality import ResearchQualityService

if TYPE_CHECKING:
    from ase.container import Container


def research_quality(container: "Container", session: AsyncSession) -> ResearchQualityService:
    return ResearchQualityService(
        SqlResearchQualityReader(session),
        container.repositories(session).llm_profiles,
        container.access_policy(session),
        container.clock,
    )
