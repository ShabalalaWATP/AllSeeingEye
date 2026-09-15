"""Team invitation workflow and authority checks."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from ase.application.auditing import Auditor
from ase.application.dto import RequestContext
from ase.application.ports import Clock, UnitOfWork, UserRepository
from ase.application.ports.directory_profile import DirectoryProfileRepository
from ase.application.ports.team_invitations import DuplicateInvitation, TeamInvitationRepository
from ase.application.ports.teams import TeamRepository
from ase.application.teams.service import MAX_TEAM_MEMBERS
from ase.domain.audit import AuditAction
from ase.domain.errors import Conflict, Forbidden, InvalidRequest, NotFound, Unauthenticated
from ase.domain.team_invitation import (
    MAX_INVITATION_NOTE,
    InvitationStatus,
    TeamInvitation,
    TeamInvitationPage,
)
from ase.domain.teams import MembershipRole, Team, TeamMembership
from ase.domain.users import Role, User

INVITATION_TTL = timedelta(days=7)
MAX_PENDING_INVITATIONS = 20


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


class TeamInvitationService:
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

    async def send(
        self,
        actor: User,
        team_id: UUID,
        recipient_id: UUID,
        note: str | None,
        context: RequestContext,
        *,
        require_discoverable: bool = True,
    ) -> TeamInvitation:
        current, team = await self._team_authority(actor, team_id)
        target = await self._users.lock_by_id(recipient_id)
        profile = await self._directory_profiles.get(target.id) if target is not None else None
        if (
            target is None
            or not target.is_active
            or profile is None
            or profile.username is None
            # Exact-handle invitations may reach a non-discoverable account that has a handle.
            or (require_discoverable and not profile.is_discoverable)
            or (target.role is Role.ADMIN and not current.is_admin)
        ):
            # One response for every ineligible account, so a Manager cannot
            # learn whether an identifier is inactive, hidden or an Administrator.
            raise InvalidRequest("Choose an eligible account from the operator directory.")
        if target.id == current.id:
            raise InvalidRequest("You are already the manager of this team.")
        if await self._teams.get_membership(team_id, target.id) is not None:
            raise Conflict("That account is already a member of this team.")
        now = self._clock.now()
        # Retire lapsed invitations inside this transaction, under the team lock,
        # so they neither block re-invitation through the partial unique index
        # nor consume the outstanding invitation allowance.
        await self._invitations.expire_lapsed(team_id, now)
        if await self._invitations.find_pending(team_id, target.id, now) is not None:
            raise Conflict("A pending invitation already exists for this account.")
        if await self._invitations.count_pending(team_id, now) >= MAX_PENDING_INVITATIONS:
            raise InvalidRequest("This team has reached its pending invitation limit.")
        invitation = TeamInvitation(
            id=uuid4(),
            team_id=team.id,
            recipient_id=target.id,
            inviter_id=current.id,
            role=MembershipRole.MEMBER,
            note=_note(note),
            status=InvitationStatus.PENDING,
            created_at=now,
            expires_at=now + INVITATION_TTL,
            team_name=team.name,
            inviter_display_name=current.display_name,
            recipient_display_name=target.display_name,
        )
        try:
            await self._invitations.add(invitation)
        except DuplicateInvitation:
            await self._uow.rollback()
            raise Conflict("A pending invitation already exists for this account.") from None
        await self._auditor.record(
            AuditAction.TEAM_INVITATION_CREATED,
            actor=current.id,
            subject=str(invitation.id),
            ip=context.ip,
            details={"team_id": str(team_id), "recipient_id": str(target.id)},
        )
        await self._uow.commit()
        return invitation

    async def authorise_sender(self, actor: User, team_id: UUID, note: str | None) -> None:
        """Check caller-side invitation preconditions without creating anything."""

        try:
            _current, _team = await self._team_authority(actor, team_id)
            _note(note)
            if (
                await self._invitations.count_pending(team_id, self._clock.now())
                >= MAX_PENDING_INVITATIONS
            ):
                raise InvalidRequest("This team has reached its pending invitation limit.")
        finally:
            await self._uow.rollback()

    async def inbox(
        self, actor: User, *, status: InvitationStatus | None, limit: int, offset: int
    ) -> TeamInvitationPage:
        current = _actor_is_fresh(actor, await self._users.get_by_id(actor.id))
        if not 1 <= limit <= 20 or not 0 <= offset <= 1000:
            raise InvalidRequest("Invalid invitation page bounds.")
        return await self._invitations.list_for_recipient(
            current.id, status=status, limit=limit, offset=offset, now=self._clock.now()
        )

    async def team_inbox(
        self,
        actor: User,
        team_id: UUID,
        *,
        status: InvitationStatus | None,
        limit: int,
        offset: int,
    ) -> TeamInvitationPage:
        _current, _team = await self._team_authority(actor, team_id, allow_archived_admin=True)
        if not 1 <= limit <= 20 or not 0 <= offset <= 1000:
            raise InvalidRequest("Invalid invitation page bounds.")
        return await self._invitations.list_for_team(
            team_id, status=status, limit=limit, offset=offset, now=self._clock.now()
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

    async def withdraw(
        self,
        actor: User,
        team_id: UUID,
        invitation_id: UUID,
        context: RequestContext,
        expected_revision: int | None,
    ) -> None:
        current, _team = await self._team_authority(actor, team_id, allow_archived_admin=True)
        invitation = await self._invitations.get_for_update(invitation_id)
        if invitation is None or invitation.team_id != team_id:
            raise NotFound()
        if expected_revision is not None and invitation.revision != expected_revision:
            raise Conflict("The invitation changed. Reload it before withdrawing it.")
        if invitation.status is not InvitationStatus.PENDING:
            return
        updated = _responded(invitation, InvitationStatus.WITHDRAWN, self._clock.now())
        await self._invitations.save(updated)
        await self._auditor.record(
            AuditAction.TEAM_INVITATION_WITHDRAWN,
            actor=current.id,
            subject=str(invitation.id),
            ip=context.ip,
            details={"team_id": str(team_id)},
        )
        await self._uow.commit()
