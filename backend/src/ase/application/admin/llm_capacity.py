"""Bound configured text profiles, including drafts, under the administration guard."""

from ase.application.ports.llm import LlmProfileRepository
from ase.domain.errors import InvalidRequest
from ase.domain.llm import TEXT_ROLES, LlmRole

MAX_TEXT_PROFILES = 5


async def require_text_capacity(profiles: LlmProfileRepository, roles: frozenset[LlmRole]) -> None:
    if roles & TEXT_ROLES:
        count = sum(bool(profile.roles & TEXT_ROLES) for profile in await profiles.list_all())
        if count >= MAX_TEXT_PROFILES:
            raise InvalidRequest(
                "You can configure up to five text models. Remove an unused model first."
            )
