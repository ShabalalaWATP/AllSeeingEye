"""HTTP contracts for directory-backed team invitations."""

from __future__ import annotations

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ase.domain.team_invitation import (
    MAX_INVITATION_NOTE,
    InvitationStatus,
    TeamInvitation,
    TeamInvitationPage,
)
from ase.domain.teams import MembershipRole


class TeamInvitationCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recipient_id: UUID
    note: str | None = Field(default=None, max_length=MAX_INVITATION_NOTE)


class TeamInvitationActionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int | None = Field(default=None, ge=1)


class TeamInvitationOut(BaseModel):
    id: UUID
    team_id: UUID
    recipient_id: UUID
    inviter_id: UUID
    role: MembershipRole
    note: str | None
    status: InvitationStatus
    created_at: datetime
    expires_at: datetime
    responded_at: datetime | None
    revision: int
    team_name: str | None
    inviter_display_name: str | None
    recipient_display_name: str | None
    recipient_username: str | None

    @classmethod
    def from_entity(cls, invitation: TeamInvitation) -> Self:
        return cls(
            id=invitation.id,
            team_id=invitation.team_id,
            recipient_id=invitation.recipient_id,
            inviter_id=invitation.inviter_id,
            role=invitation.role,
            note=invitation.note,
            status=invitation.status,
            created_at=invitation.created_at,
            expires_at=invitation.expires_at,
            responded_at=invitation.responded_at,
            revision=invitation.revision,
            team_name=invitation.team_name,
            inviter_display_name=invitation.inviter_display_name,
            recipient_display_name=invitation.recipient_display_name,
            recipient_username=invitation.recipient_username,
        )


class TeamInvitationPageOut(BaseModel):
    items: list[TeamInvitationOut]
    total: int
    offset: int
    limit: int
    next_offset: int | None

    @classmethod
    def from_page(cls, page: TeamInvitationPage) -> Self:
        return cls(
            items=[TeamInvitationOut.from_entity(item) for item in page.items],
            total=page.total,
            offset=page.offset,
            limit=page.limit,
            next_offset=page.next_offset,
        )
