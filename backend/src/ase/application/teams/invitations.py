"""Team invitation workflow and authority checks."""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from uuid import UUID, uuid4

from ase.application.auditing import Auditor
from ase.application.dto import RequestContext
from ase.application.ports import Clock, UnitOfWork, UserRepository
from ase.application.ports.directory_profile import DirectoryProfileRepository
from ase.application.ports.team_invitations import DuplicateInvitation, TeamInvitationRepository
from ase.application.ports.teams import TeamRepository
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
    ) -> TeamInvitation:
        current, team = await self._team_authority(actor, team_id)
        target = await self._users.lock_by_id(recipient_id)
        if target is None or not target.is_active:
            raise InvalidRequest("Choose an active directory account.")
        profile = await self._directory_profiles.get(target.id)
        if profile is None or not profile.is_discoverable or profile.username is None:
            raise InvalidRequest("Choose an account that is visible in the operator directory.")
        if target.role is Role.ADMIN and not current.is_admin:
            raise Forbidden("Administrators must be added by another Administrator.")
        if target.id == current.id:
            raise InvalidRequest("You are already the manager of this team.")
        if await self._teams.get_membership(team_id, target.id) is not None:
            raise Conflict("That account is already a member of this team.")
        if await self._invitations.find_pending(team_id, target.id) is not None:
            raise Conflict("A pending invitation already exists for this account.")
        if await self._invitations.count_pending(team_id) >= MAX_PENDING_INVITATIONS:
            raise InvalidRequest("This team has reached its pending invitation limit.")
        now = self._clock.now()
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

    async def inbox(
        self, actor: User, *, status: InvitationStatus | None, limit: int, offset: int
    ) -> TeamInvitationPage:
        current = _actor_is_fresh(actor, await self._users.get_by_id(actor.id))
        if not 1 <= limit <= 20 or not 0 <= offset <= 1000:
            raise InvalidRequest("Invalid invitation page bounds.")
        return await self._invitations.list_for_recipient(
            current.id, status=status, limit=limit, offset=offset
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
            team_id, status=status, limit=limit, offset=offset
        )

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
            expired = replace(
                invitation,
                status=InvitationStatus.EXPIRED,
                responded_at=now,
                revision=invitation.revision + 1,
            )
            await self._invitations.save(expired)
            await self._uow.commit()
            raise Conflict("That invitation has expired.")
        team = await self._teams.get_for_update(invitation.team_id)
        if team is None:
            raise NotFound()
        if target is InvitationStatus.DECLINED:
            updated = replace(
                invitation,
                status=target,
                responded_at=now,
                revision=invitation.revision + 1,
            )
        else:
            if not team.is_active:
                raise InvalidRequest("Archived teams cannot accept invitations.")
            inviter = await self._users.get_by_id(invitation.inviter_id)
            inviter_membership = await self._teams.get_membership(
                invitation.team_id, invitation.inviter_id
            )
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
                withdrawn = replace(
                    invitation,
                    status=InvitationStatus.WITHDRAWN,
                    responded_at=now,
                    revision=invitation.revision + 1,
                )
                await self._invitations.save(withdrawn)
                await self._uow.commit()
                raise Conflict("The inviter no longer manages this team.")
            existing = await self._teams.get_membership(invitation.team_id, current.id)
            if existing is None:
                await self._teams.put_membership(
                    TeamMembership(
                        invitation.team_id,
                        current.id,
                        invitation.role,
                        now,
                    )
                )
            updated = replace(
                invitation,
                status=target,
                responded_at=now,
                revision=invitation.revision + 1,
            )
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
        now = self._clock.now()
        updated = replace(
            invitation,
            status=InvitationStatus.WITHDRAWN,
            responded_at=now,
            revision=invitation.revision + 1,
        )
        await self._invitations.save(updated)
        await self._auditor.record(
            AuditAction.TEAM_INVITATION_WITHDRAWN,
            actor=current.id,
            subject=str(invitation.id),
            ip=context.ip,
            details={"team_id": str(team_id)},
        )
        await self._uow.commit()
