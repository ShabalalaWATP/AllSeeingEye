"""Personal and team authorisation, rebuilt from authoritative identity and membership."""

from dataclasses import dataclass
from uuid import UUID

from ase.application.ports.repositories import UserRepository
from ase.application.ports.teams import TeamRepository
from ase.domain.access import Visibility
from ase.domain.errors import Forbidden, InvalidRequest, NotFound, Unauthenticated
from ase.domain.teams import MembershipRole, Team
from ase.domain.users import User


@dataclass(frozen=True, slots=True)
class AccessContext:
    """A short-lived decision context. Rebuild after external work, never cache in a session."""

    actor: User
    teams: dict[UUID, Team]
    memberships: dict[UUID, MembershipRole]

    @property
    def visibility(self) -> Visibility:
        return Visibility(self.actor.id, self.actor.is_admin, tuple(self.memberships))

    def require_read(self, created_by: UUID | None, team_id: UUID | None) -> None:
        if self.actor.is_admin:
            return
        if team_id is None:
            allowed = created_by is not None and created_by == self.actor.id
        else:
            allowed = team_id in self.memberships
        if not allowed:
            raise NotFound()

    def require_create(self, team_id: UUID | None) -> None:
        if team_id is None:
            return
        team = self.teams.get(team_id)
        if team is None:
            raise NotFound()
        if self.actor.is_admin:
            return
        if team_id not in self.memberships:
            raise NotFound()
        if not team.is_active:
            raise Forbidden("Archived teams are read-only.")

    def require_write(self, created_by: UUID | None, team_id: UUID | None) -> None:
        self.require_read(created_by, team_id)
        if self.actor.is_admin:
            return
        self.require_create(team_id)
        if created_by == self.actor.id:
            return
        if team_id is not None and self.memberships.get(team_id) is MembershipRole.MANAGER:
            return
        raise Forbidden()

    def require_same_scope(
        self,
        created_by: UUID | None,
        team_id: UUID | None,
        linked_created_by: UUID | None,
        linked_team_id: UUID | None,
    ) -> None:
        """Even administrators may not join personal records owned by different people."""
        self.require_read(linked_created_by, linked_team_id)
        if team_id != linked_team_id or (
            team_id is None and (created_by is None or created_by != linked_created_by)
        ):
            raise InvalidRequest("Linked records must share the same personal or team scope.")


class AccessPolicy:
    def __init__(self, users: UserRepository, teams: TeamRepository) -> None:
        self._users, self._teams = users, teams

    async def background(
        self, owner_id: UUID, team_id: UUID | None, *, for_update: bool = False
    ) -> AccessContext:
        """Automation runs only for a current owner in an active originating team.

        An unavailable owner is a refusal of the work, never a failure of the caller's
        own session, so it raises Forbidden rather than Unauthenticated.
        """
        owner = await self._users.get_by_id(owner_id)
        if owner is None or not owner.is_active:
            raise Forbidden("Background work requires an active owner.")
        try:
            context = await self.context(owner, for_update=for_update)
        except Unauthenticated:
            # The owner changed between the read and the locked re-read.
            raise Forbidden("Background work requires an active owner.") from None
        if team_id is not None:
            team = context.teams.get(team_id)
            if team is None or not team.is_active or team_id not in context.memberships:
                raise Forbidden("Background work requires current membership of an active team.")
        return context

    async def context(self, actor: User, *, for_update: bool = False) -> AccessContext:
        if for_update:
            # Team membership/archive and account role/status transitions take this same
            # guard first. Keep it until commit and never across outbound/model calls.
            await self._users.lock_administration()
            current = await self._users.lock_by_id(actor.id)
        else:
            current = await self._users.get_by_id(actor.id)
        if (
            current is None
            or not current.is_active
            or current.security_version != actor.security_version
        ):
            raise Unauthenticated()
        teams = await self._teams.list_visible(current.id, administrator=current.is_admin)
        memberships = await self._teams.memberships_for_user(current.id)
        return AccessContext(
            current,
            {team.id: team for team in teams},
            {member.team_id: member.role for member in memberships},
        )
