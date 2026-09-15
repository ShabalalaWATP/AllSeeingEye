"""SQL persistence for bounded in-app team invitations."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from ase.adapters.persistence.directory_profile import DirectoryProfileRow
from ase.adapters.persistence.models import UserRow
from ase.adapters.persistence.team_invitation_models import TeamInvitationRow
from ase.adapters.persistence.teams import TeamRow
from ase.application.ports.team_invitations import DuplicateInvitation
from ase.domain.team_invitation import InvitationStatus, TeamInvitation, TeamInvitationPage
from ase.domain.teams import MembershipRole


def _invitation(
    row: TeamInvitationRow,
    *,
    team_name: str | None = None,
    inviter_display_name: str | None = None,
    recipient_display_name: str | None = None,
    recipient_username: str | None = None,
) -> TeamInvitation:
    return TeamInvitation(
        id=row.id,
        team_id=row.team_id,
        recipient_id=row.recipient_id,
        inviter_id=row.inviter_id,
        role=MembershipRole(row.role),
        note=row.note,
        status=InvitationStatus(row.status),
        created_at=row.created_at,
        expires_at=row.expires_at,
        responded_at=row.responded_at,
        revision=row.revision,
        team_name=team_name,
        inviter_display_name=inviter_display_name,
        recipient_display_name=recipient_display_name,
        recipient_username=recipient_username,
    )


class SqlTeamInvitationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, invitation: TeamInvitation) -> None:
        self._session.add(
            TeamInvitationRow(
                id=invitation.id,
                team_id=invitation.team_id,
                recipient_id=invitation.recipient_id,
                inviter_id=invitation.inviter_id,
                role=invitation.role.value,
                note=invitation.note,
                status=invitation.status.value,
                created_at=invitation.created_at,
                expires_at=invitation.expires_at,
                responded_at=invitation.responded_at,
                revision=invitation.revision,
            )
        )
        try:
            await self._session.flush()
        except IntegrityError:
            raise DuplicateInvitation() from None

    async def get(self, invitation_id: UUID) -> TeamInvitation | None:
        row = await self._session.get(TeamInvitationRow, invitation_id, populate_existing=True)
        return _invitation(row) if row else None

    async def get_for_update(self, invitation_id: UUID) -> TeamInvitation | None:
        row = await self._session.scalar(
            select(TeamInvitationRow)
            .where(TeamInvitationRow.id == invitation_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return _invitation(row) if row else None

    async def save(self, invitation: TeamInvitation) -> None:
        row = await self._session.get(TeamInvitationRow, invitation.id)
        if row is None:
            return
        row.team_id = invitation.team_id
        row.recipient_id = invitation.recipient_id
        row.inviter_id = invitation.inviter_id
        row.role = invitation.role.value
        row.note = invitation.note
        row.status = invitation.status.value
        row.created_at = invitation.created_at
        row.expires_at = invitation.expires_at
        row.responded_at = invitation.responded_at
        row.revision = invitation.revision
        await self._session.flush()

    async def find_pending(self, team_id: UUID, recipient_id: UUID) -> TeamInvitation | None:
        row = await self._session.scalar(
            select(TeamInvitationRow)
            .where(
                TeamInvitationRow.team_id == team_id,
                TeamInvitationRow.recipient_id == recipient_id,
                TeamInvitationRow.status == InvitationStatus.PENDING.value,
            )
            .order_by(TeamInvitationRow.created_at.desc())
        )
        return _invitation(row) if row else None

    async def _page(
        self,
        statement: Select[tuple[TeamInvitationRow]],
        *,
        limit: int,
        offset: int,
    ) -> TeamInvitationPage:
        total = int(
            await self._session.scalar(select(func.count()).select_from(statement.subquery())) or 0
        )
        rows = await self._session.scalars(
            statement.order_by(TeamInvitationRow.created_at.desc(), TeamInvitationRow.id)
            .limit(limit)
            .offset(offset)
            .execution_options(populate_existing=True)
        )
        items: list[TeamInvitation] = []
        for row in rows:
            team_name = await self._session.scalar(
                select(TeamRow.name).where(TeamRow.id == row.team_id)
            )
            inviter_name = await self._session.scalar(
                select(UserRow.display_name).where(UserRow.id == row.inviter_id)
            )
            recipient_name = await self._session.scalar(
                select(UserRow.display_name).where(UserRow.id == row.recipient_id)
            )
            recipient_username = await self._session.scalar(
                select(DirectoryProfileRow.username).where(
                    DirectoryProfileRow.user_id == row.recipient_id
                )
            )
            items.append(
                _invitation(
                    row,
                    team_name=team_name,
                    inviter_display_name=inviter_name,
                    recipient_display_name=recipient_name,
                    recipient_username=recipient_username,
                )
            )
        return TeamInvitationPage(tuple(items), total=total, offset=offset, limit=limit)

    async def list_for_recipient(
        self, recipient_id: UUID, *, status: InvitationStatus | None, limit: int, offset: int
    ) -> TeamInvitationPage:
        statement = select(TeamInvitationRow).where(TeamInvitationRow.recipient_id == recipient_id)
        if status is not None:
            statement = statement.where(TeamInvitationRow.status == status.value)
        return await self._page(statement, limit=limit, offset=offset)

    async def list_for_team(
        self, team_id: UUID, *, status: InvitationStatus | None, limit: int, offset: int
    ) -> TeamInvitationPage:
        statement = select(TeamInvitationRow).where(TeamInvitationRow.team_id == team_id)
        if status is not None:
            statement = statement.where(TeamInvitationRow.status == status.value)
        return await self._page(statement, limit=limit, offset=offset)

    async def count_pending(self, team_id: UUID) -> int:
        return int(
            await self._session.scalar(
                select(func.count()).where(
                    TeamInvitationRow.team_id == team_id,
                    TeamInvitationRow.status == InvitationStatus.PENDING.value,
                )
            )
            or 0
        )
