"""Team invitation workflow and authority checks."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from uuid import UUID

from ase.application.auditing import Auditor
from ase.application.ports import Clock, UnitOfWork, UserRepository
from ase.application.ports.directory_profile import DirectoryProfileRepository
from ase.application.ports.team_invitations import TeamInvitationRepository
from ase.application.ports.teams import TeamRepository
from ase.domain.errors import Forbidden, InvalidRequest, NotFound, Unauthenticated
from ase.domain.team_invitation import (
    MAX_INVITATION_NOTE,
    InvitationStatus,
    TeamInvitation,
)
from ase.domain.teams import MembershipRole, Team
from ase.domain.users import User


def _actor_is_fresh(actor: User, current: User | None) -> User:
    if (
        current is None
        or not current.is_active
        or current.security_version != actor.security_version
    ):
        raise Unauthenticated()
    return current


def _note(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value or len(value) > MAX_INVITATION_NOTE:
        raise InvalidRequest(
            f"Invitation notes must contain 1 to {MAX_INVITATION_NOTE} characters."
        )
    if any(ord(char) < 32 and char not in "\n\t" for char in value):
        raise InvalidRequest("Invitation notes contain an unsupported control character.")
    return value


def _responded(
    invitation: TeamInvitation, status: InvitationStatus, now: datetime
) -> TeamInvitation:
    return replace(invitation, status=status, responded_at=now, revision=invitation.revision + 1)


class TeamInvitationContext:
    def __init__(
        self,
        invitations: TeamInvitationRepository,
        teams: TeamRepository,
        users: UserRepository,
        directory_profiles: DirectoryProfileRepository,
        clock: Clock,
        auditor: Auditor,
        uow: UnitOfWork,
    ) -> None:
        self._invitations = invitations
        self._teams = teams
        self._users = users
        self._directory_profiles = directory_profiles
        self._clock = clock
        self._auditor = auditor
        self._uow = uow

    async def _team_authority(
        self, actor: User, team_id: UUID, *, allow_archived_admin: bool = False
    ) -> tuple[User, Team]:
        await self._users.lock_administration()
        current = _actor_is_fresh(actor, await self._users.lock_by_id(actor.id))
        team = await self._teams.get_for_update(team_id)
        membership = await self._teams.get_membership(team_id, current.id)
        if team is None or (not current.is_admin and membership is None):
            raise NotFound()
        if not current.is_admin and (
            membership is None or membership.role is not MembershipRole.MANAGER
        ):
            raise Forbidden()
        if not team.is_active and not (allow_archived_admin and current.is_admin):
            raise InvalidRequest("Archived teams are read-only.")
        return current, team
