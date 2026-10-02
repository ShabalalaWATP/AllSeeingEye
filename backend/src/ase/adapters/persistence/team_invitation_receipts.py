"""Sender receipt pagination and admission never inspect private delivery state."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnElement

from ase.adapters.persistence.team_invitation_models import TeamInvitationReceiptRow as Receipt
from ase.domain.team_invitation import InvitationStatus, TeamInvitation, TeamInvitationPage
from ase.domain.teams import MembershipRole


def _visible_status(now: datetime) -> ColumnElement[str]:
    return case(
        (and_(Receipt.status == "pending", Receipt.expires_at <= now), "expired"),
        else_=Receipt.status,
    )


def _receipt(row: Receipt, now: datetime) -> TeamInvitation:
    status = InvitationStatus(row.status)
    if status is InvitationStatus.PENDING and row.expires_at <= now:
        status = InvitationStatus.EXPIRED
    return TeamInvitation(
        id=row.id,
        team_id=row.team_id,
        recipient_id=row.recipient_id,
        inviter_id=row.inviter_id,
        role=MembershipRole.MEMBER,
        note=row.note,
        status=status,
        created_at=row.created_at,
        expires_at=row.expires_at,
        responded_at=row.responded_at,
        revision=row.revision,
        recipient_display_name=row.recipient_display_name,
        recipient_username=row.recipient_username,
    )


class SqlTeamInvitationReceipts:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_receipt(self, receipt: TeamInvitation, invitation_id: UUID | None) -> None:
        self._session.add(
            Receipt(
                id=receipt.id,
                invitation_id=invitation_id,
                team_id=receipt.team_id,
                inviter_id=receipt.inviter_id,
                recipient_id=receipt.recipient_id,
                recipient_display_name=receipt.recipient_display_name,
                recipient_username=receipt.recipient_username,
                note=receipt.note,
                status=receipt.status.value,
                created_at=receipt.created_at,
                expires_at=receipt.expires_at,
                responded_at=receipt.responded_at,
                revision=receipt.revision,
            )
        )
        await self._session.flush()

    async def get_receipt(
        self, receipt_id: UUID, now: datetime
    ) -> tuple[TeamInvitation, UUID | None] | None:
        row = await self._session.scalar(
            select(Receipt)
            .where(Receipt.id == receipt_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return (_receipt(row, now), row.invitation_id) if row else None

    async def save_receipt(self, receipt: TeamInvitation) -> None:
        row = await self._session.get(Receipt, receipt.id)
        if row is not None:
            row.status = receipt.status.value
            row.revision = receipt.revision
            row.responded_at = receipt.responded_at
            await self._session.flush()

    async def consent_receipt(
        self, invitation: TeamInvitation, display_name: str, username: str | None
    ) -> None:
        row = await self._session.scalar(
            select(Receipt).where(Receipt.invitation_id == invitation.id).with_for_update()
        )
        if row is not None and row.status == "pending":
            row.status = "accepted"
            row.responded_at = invitation.responded_at
            row.revision += 1
            row.recipient_id = invitation.recipient_id
            row.recipient_display_name = display_name
            row.recipient_username = username
            await self._session.flush()

    async def list_for_team(
        self,
        team_id: UUID,
        *,
        status: InvitationStatus | None,
        limit: int,
        offset: int,
        now: datetime,
    ) -> TeamInvitationPage:
        statement = select(Receipt).where(Receipt.team_id == team_id)
        if status is not None:
            statement = statement.where(_visible_status(now) == status.value)
        total = int(
            await self._session.scalar(select(func.count()).select_from(statement.subquery())) or 0
        )
        rows = await self._session.scalars(
            statement.order_by(Receipt.created_at.desc(), Receipt.id).limit(limit).offset(offset)
        )
        return TeamInvitationPage(tuple(_receipt(row, now) for row in rows), total, offset, limit)

    async def count_pending(self, team_id: UUID, now: datetime) -> int:
        return int(
            await self._session.scalar(
                select(func.count())
                .select_from(Receipt)
                .where(Receipt.team_id == team_id, _visible_status(now) == "pending")
            )
            or 0
        )
