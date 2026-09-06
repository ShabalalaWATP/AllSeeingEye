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


def _name(value: str) -> str:
    result = value.strip()
    if not result or len(result) > 120 or any(ord(char) < 32 for char in result):
        raise InvalidRequest("Team names must contain 1 to 120 printable characters.")
    return result


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

    async def create(self, actor: User, name: str, context: RequestContext) -> Team:
        actor = await self._actor(actor, mutation=True)
        if not actor.is_admin:
            raise Forbidden()
        now = self._clock.now()
        team = Team(uuid4(), _name(name), True, actor.id, now, now)
        await self._teams.add(team)
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
        context: RequestContext,
    ) -> Team:
        actor = await self._actor(actor, mutation=True)
        if not actor.is_admin:
            raise Forbidden()
        team = await self._teams.get_for_update(team_id)
        if team is None:
            raise NotFound()
        changes: dict[str, object] = {}
        if name is not None:
            team.name = _name(name)
            changes["name"] = team.name
        if is_active is not None:
            team.is_active = is_active
            changes["is_active"] = is_active
        if not changes:
            raise InvalidRequest("Supply a team name or active status.")
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

    async def _membership_actor(self, actor: User, team_id: UUID) -> User:
        actor = await self._actor(actor, mutation=True)
        team = await self._teams.get_for_update(team_id)
        membership = await self._teams.get_membership(team_id, actor.id)
        if team is None or (not actor.is_admin and membership is None):
            raise NotFound()
        if not actor.is_admin and not (
            actor.role is Role.MANAGER
            and membership is not None
            and membership.role is MembershipRole.MANAGER
        ):
            raise Forbidden()
        if not team.is_active:
            raise InvalidRequest(
                "Archived teams are read-only. An administrator can reactivate them."
            )
        return actor

    async def set_member(
        self,
        actor: User,
        team_id: UUID,
        *,
        email: str,
        role: MembershipRole,
        context: RequestContext,
    ) -> TeamMembership:
        actor = await self._membership_actor(actor, team_id)
        email = normalise_email(email)
        if len(email) > 320 or email.count("@") != 1 or any(char.isspace() for char in email):
            raise InvalidRequest("Supply a valid account email address.")
        target = await self._users.get_by_email(email)
        if target is None:
            raise InvalidRequest("An eligible active account could not be added.")
        target = await self._users.lock_by_id(target.id)
        if target is None or not target.is_active:
            raise InvalidRequest("An eligible active account could not be added.")
        existing = await self._teams.get_membership(team_id, target.id)
        if not actor.is_admin and (
            target.role is not Role.USER
            or role is not MembershipRole.MEMBER
            or (existing is not None and existing.role is not MembershipRole.MEMBER)
        ):
            raise Forbidden()
        if role is MembershipRole.MANAGER and target.role not in (Role.MANAGER, Role.ADMIN):
            raise InvalidRequest("Team managers must have a manager or administrator account role.")
        member = TeamMembership(
            team_id, target.id, role, existing.joined_at if existing else self._clock.now()
        )
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

    async def remove_member(
        self, actor: User, team_id: UUID, user_id: UUID, context: RequestContext
    ) -> None:
        actor = await self._membership_actor(actor, team_id)
        membership = await self._teams.get_membership(team_id, user_id)
        if membership is None:
            raise NotFound()
        target = await self._users.lock_by_id(user_id)
        if not actor.is_admin and (
            target is None
            or target.role is not Role.USER
            or membership.role is not MembershipRole.MEMBER
        ):
            raise Forbidden()
        await self._teams.remove_membership(team_id, user_id)
        await self._auditor.record(
            AuditAction.TEAM_MEMBER_REMOVED,
            actor=actor.id,
            subject=str(team_id),
            ip=context.ip,
            details={"user_id": str(user_id)},
        )
        await self._uow.commit()
