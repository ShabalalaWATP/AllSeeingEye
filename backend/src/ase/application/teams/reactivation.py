"""Explicit, atomic administrator recovery of an archived team's management."""

from uuid import UUID

from ase.application.auditing import Auditor
from ase.application.dto import RequestContext
from ase.application.ports import Clock, UserRepository
from ase.application.ports.teams import TeamRepository
from ase.domain.audit import AuditAction
from ase.domain.errors import Forbidden, InvalidRequest
from ase.domain.teams import MembershipRole, Team, TeamMembership
from ase.domain.users import User


async def prepare_reactivation(
    actor: User,
    team: Team,
    manager_id: UUID | None,
    *,
    teams: TeamRepository,
    users: UserRepository,
    clock: Clock,
    auditor: Auditor,
    context: RequestContext,
    max_members: int,
) -> None:
    """Caller holds administration, ordered account and team locks until commit."""
    if manager_id is not None:
        if not actor.is_admin:
            raise Forbidden()
        if manager_id == actor.id:
            raise Forbidden("Ask another Administrator to change an Administrator membership.")
        target = await users.get_by_id(manager_id)
        if target is None or not target.is_active:
            raise InvalidRequest(
                "Choose an active account as the team's Manager.",
                fields={"reactivation_manager_id": "Choose an active account."},
            )
        existing = await teams.get_membership(team.id, manager_id)
        if existing is None and await teams.count_members(team.id) >= max_members:
            raise InvalidRequest(f"A team can have at most {max_members} members.")
        if existing is None or existing.role is not MembershipRole.MANAGER:
            await teams.put_membership(
                TeamMembership(
                    team.id,
                    manager_id,
                    MembershipRole.MANAGER,
                    existing.joined_at if existing else clock.now(),
                )
            )
            await auditor.record(
                AuditAction.TEAM_MEMBER_SET,
                actor=actor.id,
                subject=str(team.id),
                ip=context.ip,
                details={"user_id": str(manager_id), "role": "manager", "reactivation": True},
            )
    if await teams.count_active_managers(team.id) == 0:
        raise InvalidRequest("Choose an active Manager before reactivating this team.")
