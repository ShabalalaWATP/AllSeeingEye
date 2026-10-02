"""Team invitation workflow and authority checks."""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID, uuid4

from ase.application.dto import RequestContext
from ase.application.ports.team_invitations import DuplicateInvitation
from ase.application.teams.invitation_context import TeamInvitationContext, _note, _responded
from ase.domain.audit import AuditAction
from ase.domain.errors import Conflict, Forbidden, InvalidRequest, NotFound
from ase.domain.team_invitation import (
    InvitationStatus,
    TeamInvitation,
    TeamInvitationPage,
)
from ase.domain.teams import MembershipRole
from ase.domain.users import Role, User

INVITATION_TTL = timedelta(days=7)
MAX_PENDING_INVITATIONS = 20


class TeamInvitationSender(TeamInvitationContext):
    async def send(
        self,
        actor: User,
        team_id: UUID,
        recipient_id: UUID,
        note: str | None,
        context: RequestContext,
        *,
        require_discoverable: bool = True,
        opaque: bool = False,
        commit: bool = True,
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
        if not opaque:
            await self._invitations.add_receipt(invitation, invitation.id)
        if commit:
            await self._uow.commit()
        return invitation

    async def authorise_sender(self, actor: User, team_id: UUID, note: str | None) -> None:
        """Check caller-side invitation preconditions without creating anything."""

        try:
            _current, _team = await self._team_authority(actor, team_id)
            _note(note)
        finally:
            await self._uow.rollback()

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

    async def withdraw(
        self,
        actor: User,
        team_id: UUID,
        invitation_id: UUID,
        context: RequestContext,
        expected_revision: int | None,
    ) -> None:
        current, _team = await self._team_authority(actor, team_id, allow_archived_admin=True)
        found = await self._invitations.get_receipt(invitation_id, self._clock.now())
        if found is None:
            # Pre-receipt deliveries remain revocable by their previously known ID.
            # Uniform success and no revision check keep recipient activity private.
            # The repository excludes modern deliveries linked to a different receipt.
            delivery = await self._invitations.get_unreceipted_for_update(team_id, invitation_id)
            if delivery is not None and delivery.status is InvitationStatus.PENDING:
                await self._invitations.save(
                    _responded(delivery, InvitationStatus.WITHDRAWN, self._clock.now())
                )
                await self._auditor.record(
                    AuditAction.TEAM_INVITATION_WITHDRAWN,
                    actor=current.id,
                    subject=str(delivery.id),
                    ip=context.ip,
                    details={"team_id": str(team_id)},
                )
            await self._uow.commit()
            return
        if found[0].team_id != team_id:
            raise NotFound()
        receipt, delivery_id = found
        if expected_revision is not None and receipt.revision != expected_revision:
            raise Conflict("The invitation changed. Reload it before withdrawing it.")
        if receipt.status is not InvitationStatus.PENDING:
            return
        await self._invitations.save_receipt(
            _responded(receipt, InvitationStatus.WITHDRAWN, self._clock.now())
        )
        if delivery_id is not None:
            delivery = await self._invitations.get_for_update(delivery_id)
            if delivery is not None and delivery.status is InvitationStatus.PENDING:
                await self._invitations.save(
                    _responded(delivery, InvitationStatus.WITHDRAWN, self._clock.now())
                )
        await self._auditor.record(
            AuditAction.TEAM_INVITATION_WITHDRAWN,
            actor=current.id,
            subject=str(receipt.id),
            ip=context.ip,
            details={"team_id": str(team_id)},
        )
        await self._uow.commit()

    async def submit_handle(
        self,
        actor: User,
        team_id: UUID,
        recipient_id: UUID | None,
        note: str | None,
        context: RequestContext,
    ) -> None:
        current, team = await self._team_authority(actor, team_id)
        clean_note = _note(note)
        if (
            await self._invitations.count_pending(team_id, self._clock.now())
            >= MAX_PENDING_INVITATIONS
        ):
            raise InvalidRequest("This team has reached its pending invitation limit.")
        delivery: TeamInvitation | None = None
        if recipient_id is not None:
            try:
                delivery = await self.send(
                    actor,
                    team_id,
                    recipient_id,
                    note,
                    context,
                    require_discoverable=False,
                    opaque=True,
                    commit=False,
                )
            except (Conflict, Forbidden, InvalidRequest, NotFound):
                await self._uow.rollback()
                current, team = await self._team_authority(actor, team_id)
                if (
                    await self._invitations.count_pending(team_id, self._clock.now())
                    >= MAX_PENDING_INVITATIONS
                ):
                    raise InvalidRequest(
                        "This team has reached its pending invitation limit."
                    ) from None
        now = self._clock.now()
        receipt = TeamInvitation(
            id=uuid4(),
            team_id=team.id,
            recipient_id=None,
            inviter_id=current.id,
            role=MembershipRole.MEMBER,
            note=clean_note,
            status=InvitationStatus.PENDING,
            created_at=now,
            expires_at=now + INVITATION_TTL,
        )
        await self._invitations.add_receipt(receipt, delivery.id if delivery else None)
        await self._uow.commit()
