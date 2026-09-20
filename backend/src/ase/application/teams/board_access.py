"""Current authority for one caller on one team board."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from ase.application.ports import UserRepository
from ase.application.ports.teams import TeamRepository
from ase.domain.errors import Conflict, InvalidRequest, NotFound, Unauthenticated
from ase.domain.team_board import TeamBoardPost
from ase.domain.teams import MembershipRole, Team, TeamMembership
from ase.domain.users import User

STALE_POST = "This post changed. Reload it before saving again."


@dataclass(frozen=True, slots=True)
class BoardActor:
    user: User
    team: Team
    membership: TeamMembership | None

    @property
    def moderator(self) -> bool:
        """Administrators and this team's Managers may pin and remove others' posts."""
        return self.user.is_admin or (
            self.membership is not None and self.membership.role is MembershipRole.MANAGER
        )


async def board_actor(
    users: UserRepository,
    teams: TeamRepository,
    actor: User,
    team_id: UUID,
    *,
    write: bool,
    mutation: bool = False,
) -> BoardActor:
    """Rebuild authority from the current account and membership, never from the token."""
    if write or mutation:
        # Match membership, archive and account mutation ordering. All repositories
        # share the caller's transaction, so authority remains protected until commit.
        await users.lock_administration()
        current = await users.lock_by_id(actor.id)
    else:
        current = await users.get_by_id(actor.id)
    if (
        current is None
        or not current.is_active
        or current.security_version != actor.security_version
    ):
        raise Unauthenticated()
    team = await teams.get_for_update(team_id) if write or mutation else await teams.get(team_id)
    membership = await teams.get_membership(team_id, current.id)
    if team is None or (not current.is_admin and membership is None):
        raise NotFound()
    if write and not team.is_active:
        raise InvalidRequest("Archived teams are read-only.")
    return BoardActor(current, team, membership)


def require_revision(post: TeamBoardPost, expected_revision: int) -> None:
    if expected_revision != post.revision:
        raise Conflict(STALE_POST)
