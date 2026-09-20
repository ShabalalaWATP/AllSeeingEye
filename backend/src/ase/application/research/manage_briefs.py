"""Brief ownership, revision policy and scope independent of HTTP and SQL."""

from dataclasses import replace
from datetime import UTC, timedelta
from uuid import UUID, uuid4

from ase.application.access import AccessContext, AccessPolicy
from ase.application.ports.brief_management import (
    BriefDraft,
    BriefManagementRepository,
    BriefSummary,
)
from ase.application.ports.repositories import UnitOfWork
from ase.application.ports.services import Clock
from ase.domain.errors import Conflict, Forbidden, NotFound
from ase.domain.research_brief import ResearchBrief
from ase.domain.research_brief_values import BriefIdentity
from ase.domain.users import User


class BriefScopeChange(ValueError):
    """A revision cannot change the immutable scope of its root brief."""


def _write_teams(access: AccessContext, team_id: UUID | None) -> tuple[UUID, ...]:
    teams = tuple(access.memberships)
    if access.actor.is_admin and team_id is not None and team_id not in access.memberships:
        return (*teams, team_id)
    return teams


class ManageResearchBriefs:
    def __init__(
        self,
        repository: BriefManagementRepository,
        access: AccessPolicy,
        clock: Clock,
        uow: UnitOfWork,
    ) -> None:
        self._repository, self._access, self._clock, self._uow = repository, access, clock, uow

    async def commit(self) -> None:
        """Commit only after transport validation and the caller's expiry check."""
        await self._uow.commit()

    async def list(
        self, actor: User, limit: int, offset: int, brief_id: UUID | None = None
    ) -> list[BriefSummary]:
        access = await self._access.context(actor)
        if brief_id is not None:
            await self.get_authorised(access, brief_id)
        return await self._repository.list_visible(access.visibility, limit, offset, brief_id)

    async def get_authorised(
        self, access: AccessContext, brief_id: UUID, revision: int | None = None
    ) -> ResearchBrief:
        brief = await self._repository.visible(access.visibility, brief_id, revision)
        if brief is None:
            raise NotFound("Research Brief not found.")
        return brief

    async def get(self, actor: User, brief_id: UUID, revision: int | None = None) -> ResearchBrief:
        return await self.get_authorised(await self._access.context(actor), brief_id, revision)

    async def create(self, actor: User, draft: BriefDraft) -> ResearchBrief:
        access = await self._access.context(actor, for_update=True)
        access.require_create(draft.team_id)
        now = self._clock.now().astimezone(UTC)
        identity = BriefIdentity(
            id=uuid4(),
            revision=1,
            owner_id=actor.id,
            team_id=draft.team_id,
            title=draft.title,
            preset_id=draft.preset_id,
            preset_version=draft.preset_version,
            created_at=now,
            revised_at=now,
        )
        return await self._repository.add_revision(
            draft.to_brief(identity),
            actor_id=actor.id,
            authorised_team_ids=_write_teams(access, draft.team_id),
        )

    async def revise(
        self, actor: User, brief_id: UUID, base_revision: int, draft: BriefDraft
    ) -> ResearchBrief:
        access = await self._access.context(actor, for_update=True)
        prior = await self.get_authorised(access, brief_id)
        identity = prior.identity
        access.require_write(identity.owner_id, identity.team_id)
        if identity.owner_id != actor.id:
            raise Forbidden("Only the Research Brief owner can add a revision.")
        if draft.team_id != identity.team_id:
            raise BriefScopeChange()
        if base_revision != identity.revision:
            raise Conflict("The Research Brief has a newer revision.")
        revised = replace(
            identity,
            revision=identity.revision + 1,
            title=draft.title,
            preset_id=draft.preset_id,
            preset_version=draft.preset_version,
            revised_at=max(
                self._clock.now().astimezone(UTC), identity.revised_at + timedelta(microseconds=1)
            ),
            published=False,
        )
        return await self._repository.add_revision(
            draft.to_brief(revised),
            actor_id=actor.id,
            authorised_team_ids=_write_teams(access, draft.team_id),
        )
