"""Audited team management. Global manager capability never grants global team access."""

from __future__ import annotations

from uuid import UUID, uuid4

from ase.application.auditing import Auditor
from ase.application.dto import RequestContext
from ase.application.ports.repositories import UnitOfWork, UserRepository
from ase.application.ports.services import Clock
from ase.application.ports.teams import TeamRepository
from ase.domain.audit import AuditAction
from ase.domain.errors import Forbidden, InvalidRequest, NotFound, Unauthenticated
from ase.domain.teams import MembershipRole, Team, TeamMember, TeamMembership
from ase.domain.users import Role, User, normalise_email

DESCRIPTION_UNSET = object()
MAX_ACTIVE_TEAMS_PER_ACCOUNT = 5
MAX_TEAM_MEMBERS = 100
LAST_MANAGER_MESSAGE = "Each active team must retain at least one active Manager."
DIRECT_ADD_MESSAGE = "Team Managers add people by sending an invitation."


def _name(value: str) -> str:
    result = value.strip()
    if not result or len(result) > 120 or any(ord(char) < 32 for char in result):
        raise InvalidRequest("Team names must contain 1 to 120 printable characters.")
    return result


def _description(value: str | None) -> str | None:
    if value is None:
        return None
    result = value.strip()
    if len(result) > 500 or any(ord(char) < 32 for char in result):
        raise InvalidRequest("Team descriptions must contain at most 500 printable characters.")
    return result or None


class TeamService:
    def __init__(
        self,
        teams: TeamRepository,
        users: UserRepository,
        clock: Clock,
        auditor: Auditor,
        uow: UnitOfWork,
    ) -> None:
        self._teams = teams
        self._users = users
        self._clock = clock
        self._auditor = auditor
        self._uow = uow

    async def _actor(self, actor: User, *, mutation: bool = False) -> User:
        if mutation:
            # The shared account guard also serialises role/status changes. Acquire it
            # before any user/team lock; never hold these locks during outbound work.
            await self._users.lock_administration()
            fresh = await self._users.lock_by_id(actor.id)
        else:
            fresh = await self._users.get_by_id(actor.id)
        if fresh is None or not fresh.is_active or fresh.security_version != actor.security_version:
            raise Unauthenticated()
        return fresh

    async def list_teams(self, actor: User) -> list[Team]:
        actor = await self._actor(actor)
        return await self._teams.list_visible(actor.id, administrator=actor.is_admin)

    async def get(self, actor: User, team_id: UUID) -> Team:
        actor = await self._actor(actor)
        team = await self._teams.get(team_id)
        if team is None or (
            not actor.is_admin and await self._teams.get_membership(team_id, actor.id) is None
        ):
            # Do not disclose another team's existence through direct identifiers.
            raise NotFound()
        return team

    async def roster(self, actor: User, team_id: UUID) -> tuple[Team, list[TeamMember]]:
        team = await self.get(actor, team_id)
        return team, await self._teams.list_members(team_id)

    async def create(
        self,
        actor: User,
        name: str,
        context: RequestContext,
        *,
        description: str | None = None,
    ) -> Team:
        actor = await self._actor(actor, mutation=True)
        if (
            not actor.is_admin
            and await self._teams.count_active_created_by(actor.id) >= MAX_ACTIVE_TEAMS_PER_ACCOUNT
        ):
            raise InvalidRequest(
                f"An account can create at most {MAX_ACTIVE_TEAMS_PER_ACCOUNT} active teams."
            )
        now = self._clock.now()
        team = Team(uuid4(), _name(name), True, actor.id, now, now, _description(description))
        await self._teams.add(team)
        # The creator's membership is part of the same transaction as the team
        # row. This makes a newly created team immediately usable and prevents
        # an orphaned team with no Manager after a successful response.
        await self._teams.put_membership(
            TeamMembership(team.id, actor.id, MembershipRole.MANAGER, now)
        )
        await self._auditor.record(
            AuditAction.TEAM_CREATED, actor=actor.id, subject=str(team.id), ip=context.ip
        )
        await self._uow.commit()
        return team

    async def update(
        self,
        actor: User,
        team_id: UUID,
        *,
        name: str | None,
        is_active: bool | None,
        description: str | object | None = DESCRIPTION_UNSET,
        context: RequestContext,
    ) -> Team:
        actor, team = await self._team_editor(actor, team_id, allow_archived=True)
        changes: dict[str, object] = {}
        if name is not None:
            team.name = _name(name)
            changes["name"] = team.name
        if is_active is not None:
            team.is_active = is_active
            changes["is_active"] = is_active
        if description is not DESCRIPTION_UNSET:
            if description is not None and not isinstance(description, str):
                raise InvalidRequest("Supply a valid team description.")
            team.description = _description(description)
            changes["description"] = team.description
        if not changes:
            raise InvalidRequest("Supply a team name, description or active status.")
        team.updated_at = self._clock.now()
        await self._teams.save(team)
        await self._auditor.record(
            AuditAction.TEAM_UPDATED,
            actor=actor.id,
            subject=str(team.id),
            ip=context.ip,
            details=changes,
        )
        await self._uow.commit()
        return team

    async def _team_editor(
        self, actor: User, team_id: UUID, *, allow_archived: bool = False
    ) -> tuple[User, Team]:
        """Reload a team and require its current Manager or Administrator authority."""
        actor = await self._actor(actor, mutation=True)
        team = await self._teams.get_for_update(team_id)
        membership = await self._teams.get_membership(team_id, actor.id)
        if team is None or (not actor.is_admin and membership is None):
            raise NotFound()
        if not actor.is_admin and (
            membership is None or membership.role is not MembershipRole.MANAGER
        ):
            raise Forbidden()
        if not team.is_active and not (allow_archived and actor.is_admin):
            raise InvalidRequest(
                "Archived teams are read-only. An administrator can reactivate them."
            )
        return actor, team

    async def _membership_actor(self, actor: User, team_id: UUID) -> User:
        actor, _ = await self._team_editor(actor, team_id)
        return actor

    async def _keep_active_manager(
        self, team_id: UUID, membership: TeamMembership, target: User
    ) -> None:
        """Refuse only a change that would leave no active Manager.

        An inactive Manager does not count towards the invariant, so removing or
        demoting one never reduces the active count. Callers hold the
        administration guard and team lock, which serialises concurrent attempts.
        """
        if (
            membership.role is MembershipRole.MANAGER
            and target.is_active
            and await self._teams.count_active_managers(team_id) <= 1
        ):
            raise InvalidRequest(LAST_MANAGER_MESSAGE)

    async def set_member(
        self,
        actor: User,
        team_id: UUID,
        *,
        email: str,
        role: MembershipRole,
        context: RequestContext,
    ) -> TeamMembership:
        """Administrator-only direct add by email. Managers invite people instead."""
        actor = await self._membership_actor(actor, team_id)
        if not actor.is_admin:
            # Decided before any account lookup so the response cannot reveal
            # whether an email exists, is inactive or belongs to an Administrator.
            raise Forbidden(DIRECT_ADD_MESSAGE)
        email = normalise_email(email)
        if len(email) > 320 or email.count("@") != 1 or any(char.isspace() for char in email):
            raise InvalidRequest("Supply a valid account email address.")
        target = await self._users.get_by_email(email)
        if target is None:
            raise InvalidRequest("An eligible active account could not be added.")
        target = await self._users.lock_by_id(target.id)
        if target is None or not target.is_active:
            raise InvalidRequest("An eligible active account could not be added.")
        if target.id == actor.id:
            raise Forbidden("Ask another Administrator to change an Administrator membership.")
        existing = await self._teams.get_membership(team_id, target.id)
        if existing is None and await self._teams.count_members(team_id) >= MAX_TEAM_MEMBERS:
            raise InvalidRequest(f"A team can have at most {MAX_TEAM_MEMBERS} members.")
        if existing is not None and role is MembershipRole.MEMBER:
            await self._keep_active_manager(team_id, existing, target)
        member = TeamMembership(
            team_id, target.id, role, existing.joined_at if existing else self._clock.now()
        )
        await self._teams.put_membership(member)
        await self._auditor.record(
            AuditAction.TEAM_MEMBER_SET,
            actor=actor.id,
            subject=str(team_id),
            ip=context.ip,
            details={
                "user_id": str(target.id),
                "role": role.value,
                "direct_add": existing is None,
            },
        )
        await self._uow.commit()
        return member

    async def change_role(
        self,
        actor: User,
        team_id: UUID,
        user_id: UUID,
        role: MembershipRole,
        context: RequestContext,
    ) -> TeamMembership:
        """Promote or demote an existing member, identified by account id."""
        actor = await self._membership_actor(actor, team_id)
        existing = await self._teams.get_membership(team_id, user_id)
        target = await self._users.lock_by_id(user_id) if existing is not None else None
        if existing is None or target is None:
            raise NotFound()
        if not actor.is_admin and target.role is Role.ADMIN:
            raise Forbidden()
        if actor.is_admin and target.id == actor.id:
            raise Forbidden("Ask another Administrator to change an Administrator membership.")
        if role is MembershipRole.MANAGER and not target.is_active:
            raise InvalidRequest("Only an active account can be made a Manager.")
        if role is MembershipRole.MEMBER:
            await self._keep_active_manager(team_id, existing, target)
        member = TeamMembership(team_id, target.id, role, existing.joined_at)
        if existing.role is not role:
            await self._teams.put_membership(member)
            await self._auditor.record(
                AuditAction.TEAM_MEMBER_SET,
                actor=actor.id,
                subject=str(team_id),
                ip=context.ip,
                details={"user_id": str(target.id), "role": role.value},
            )
        await self._uow.commit()
        return member

    async def leave(self, actor: User, team_id: UUID, context: RequestContext) -> None:
        """Leave a team while preserving its final active Manager invariant."""
        actor = await self._actor(actor, mutation=True)
        team = await self._teams.get_for_update(team_id)
        membership = await self._teams.get_membership(team_id, actor.id)
        if team is None or membership is None:
            raise NotFound()
        if not team.is_active:
            raise InvalidRequest(
                "Archived teams are read-only. An administrator can reactivate them."
            )
        if actor.is_admin:
            raise Forbidden("Ask another Administrator to remove an administrator membership.")
        await self._keep_active_manager(team_id, membership, actor)
        await self._teams.remove_membership(team_id, actor.id)
        await self._auditor.record(
            AuditAction.TEAM_MEMBER_LEFT,
            actor=actor.id,
            subject=str(team_id),
            ip=context.ip,
            details={"user_id": str(actor.id)},
        )
        await self._uow.commit()

    async def remove_member(
        self, actor: User, team_id: UUID, user_id: UUID, context: RequestContext
    ) -> None:
        actor = await self._membership_actor(actor, team_id)
        membership = await self._teams.get_membership(team_id, user_id)
        if membership is None:
            raise NotFound()
        target = await self._users.lock_by_id(user_id)
        if target is None:
            raise NotFound()
        if not actor.is_admin and target.role is Role.ADMIN:
            raise Forbidden()
        if actor.is_admin and target.id == actor.id:
            raise Forbidden("Ask another Administrator to remove an Administrator membership.")
        await self._keep_active_manager(team_id, membership, target)
        await self._teams.remove_membership(team_id, user_id)
        await self._auditor.record(
            AuditAction.TEAM_MEMBER_REMOVED,
            actor=actor.id,
            subject=str(team_id),
            ip=context.ip,
            details={"user_id": str(user_id)},
        )
        await self._uow.commit()
