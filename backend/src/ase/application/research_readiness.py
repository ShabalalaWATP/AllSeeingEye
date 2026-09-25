"""Whether research generation can reach a model, reduced to a yes or no.

Ordinary users learn only this boolean: never a provider, endpoint, model or key. The
answer uses the same routing rules as a real run, without calling a provider, for the
destinations the caller can save research to: their personal workspace and the active
teams they belong to. A broken assignment still fails closed, exactly as a run would.
"""

from uuid import UUID

from ase.application.model_routing import ModelRouting
from ase.application.ports.llm import LlmBindingRepository, LlmProfileRepository
from ase.application.ports.teams import TeamRepository
from ase.domain.errors import NoModelAvailable
from ase.domain.llm import LlmRole


class ResearchReadiness:
    def __init__(
        self,
        profiles: LlmProfileRepository,
        bindings: LlmBindingRepository,
        teams: TeamRepository,
    ) -> None:
        self._routing = ModelRouting(profiles, bindings)
        self._teams = teams

    async def available(self, user_id: UUID) -> bool:
        """True when at least one of the caller's research destinations resolves a model."""
        if await self._routes(personal_owner_id=user_id):
            return True
        for team in await self._teams.list_visible(user_id, administrator=False):
            if team.is_active and await self._routes(team_id=team.id):
                return True
        return False

    async def _routes(
        self, *, team_id: UUID | None = None, personal_owner_id: UUID | None = None
    ) -> bool:
        try:
            await self._routing.snapshot(
                team_id=team_id, personal_owner_id=personal_owner_id, role=LlmRole.ASSESSMENT
            )
        except NoModelAvailable:
            return False
        return True
