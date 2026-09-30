"""Team invitation workflow and authority checks."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from ase.application.dto import RequestContext
from ase.application.teams.invitation_context import _actor_is_fresh, _responded
from ase.application.teams.invitation_sender import TeamInvitationSender
from ase.application.teams.service import MAX_TEAM_MEMBERS
from ase.domain.audit import AuditAction
from ase.domain.errors import Conflict, InvalidRequest, NotFound
from ase.domain.team_invitation import (
    InvitationStatus,
    TeamInvitation,
    TeamInvitationPage,
)
from ase.domain.teams import MembershipRole, Team, TeamMembership
from ase.domain.users import User


class TeamInvitationService(TeamInvitationSender):
    async def inbox(
        self, actor: User, *, status: InvitationStatus | None, limit: int, offset: int
    ) -> TeamInvitationPage:
        current = _actor_is_fresh(actor, await self._users.get_by_id(actor.id))
        if not 1 <= limit <= 20 or not 0 <= offset <= 1000:
            raise InvalidRequest("Invalid invitation page bounds.")
        return await self._invitations.list_for_recipient(
            current.id, status=status, limit=limit, offset=offset, now=self._clock.now()
        )

    async def _join(
        self, invitation: TeamInvitation, current: User, team: Team, now: datetime
    ) -> None:
        """Recheck team and inviter authority, then add the membership under the team lock."""
        if not team.is_active:
            raise InvalidRequest("Archived teams cannot accept invitations.")
        inviter = await self._users.get_by_id(invitation.inviter_id)
        inviter_membership = await self._teams.get_membership(team.id, invitation.inviter_id)
        if (
            inviter is None
            or not inviter.is_active
            or (
                not inviter.is_admin
                and (
                    inviter_membership is None
                    or inviter_membership.role is not MembershipRole.MANAGER
                )
            )
        ):
            await self._invitations.save(_responded(invitation, InvitationStatus.WITHDRAWN, now))
            await self._uow.commit()
            raise Conflict("The inviter no longer manages this team.")
        if await self._teams.get_membership(team.id, current.id) is not None:
            return
        # The team row lock is held, so concurrent acceptances cannot together
        # exceed the roster cap.
        if await self._teams.count_members(team.id) >= MAX_TEAM_MEMBERS:
            raise InvalidRequest(f"A team can have at most {MAX_TEAM_MEMBERS} members.")
        await self._teams.put_membership(TeamMembership(team.id, current.id, invitation.role, now))

    async def _transition(
        self,
        actor: User,
        invitation_id: UUID,
        target: InvitationStatus,
        context: RequestContext,
        *,
        expected_revision: int | None = None,
    ) -> TeamInvitation:
        await self._users.lock_administration()
        current = _actor_is_fresh(actor, await self._users.lock_by_id(actor.id))
        invitation = await self._invitations.get_for_update(invitation_id)
        if invitation is None:
            raise NotFound()
        if invitation.recipient_id != current.id:
            raise NotFound()
        if expected_revision is not None and expected_revision != invitation.revision:
            raise Conflict("The invitation changed. Reload it before responding.")
        if invitation.status is target:
            await self._uow.rollback()
            return invitation
        if invitation.status is not InvitationStatus.PENDING:
            raise Conflict("That invitation is no longer pending.")
        now = self._clock.now()
        if invitation.expires_at <= now:
            await self._invitations.save(_responded(invitation, InvitationStatus.EXPIRED, now))
            await self._uow.commit()
            raise Conflict("That invitation has expired.")
        team = await self._teams.get_for_update(invitation.team_id)
        if team is None:
            raise NotFound()
        if target is InvitationStatus.ACCEPTED:
            await self._join(invitation, current, team, now)
        updated = _responded(invitation, target, now)
        await self._invitations.save(updated)
        if target is InvitationStatus.ACCEPTED:
            profile = await self._directory_profiles.get(current.id)
            await self._invitations.consent_receipt(
                updated, current.display_name, profile.username if profile else None
            )
        action = (
            AuditAction.TEAM_INVITATION_ACCEPTED
            if target is InvitationStatus.ACCEPTED
            else AuditAction.TEAM_INVITATION_DECLINED
        )
        await self._auditor.record(
            action,
            actor=current.id,
            subject=str(invitation.id),
            ip=context.ip,
            details={"team_id": str(invitation.team_id)},
        )
        await self._uow.commit()
        return updated

    async def accept(
        self,
        actor: User,
        invitation_id: UUID,
        context: RequestContext,
        expected_revision: int | None,
    ) -> TeamInvitation:
        return await self._transition(
            actor,
            invitation_id,
            InvitationStatus.ACCEPTED,
            context,
            expected_revision=expected_revision,
        )

    async def decline(
        self,
        actor: User,
        invitation_id: UUID,
        context: RequestContext,
        expected_revision: int | None,
    ) -> TeamInvitation:
        return await self._transition(
            actor,
            invitation_id,
            InvitationStatus.DECLINED,
            context,
            expected_revision=expected_revision,
        )
