"""Persistence boundary for in-app team invitations."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from ase.domain.team_invitation import InvitationStatus, TeamInvitation, TeamInvitationPage


class DuplicateInvitation(Exception):
    """The recipient already holds a pending invitation to the team."""


class TeamInvitationRepository(Protocol):
    async def add_receipt(self, receipt: TeamInvitation, invitation_id: UUID | None) -> None: ...
    async def get_receipt(
        self, receipt_id: UUID, now: datetime
    ) -> tuple[TeamInvitation, UUID | None] | None: ...
    async def save_receipt(self, receipt: TeamInvitation) -> None: ...
    async def consent_receipt(
        self, invitation: TeamInvitation, display_name: str, username: str | None
    ) -> None: ...

    async def add(self, invitation: TeamInvitation) -> None: ...

    async def get(self, invitation_id: UUID) -> TeamInvitation | None: ...

    async def get_for_update(self, invitation_id: UUID) -> TeamInvitation | None: ...

    async def get_unreceipted_for_update(
        self, team_id: UUID, invitation_id: UUID
    ) -> TeamInvitation | None:
        """Find a legacy delivery for known-ID revocation, never for sender listing."""
        ...

    async def save(self, invitation: TeamInvitation) -> None: ...

    async def find_pending(
        self, team_id: UUID, recipient_id: UUID, now: datetime
    ) -> TeamInvitation | None:
        """Return an unexpired pending invitation."""
        ...

    async def expire_lapsed(self, team_id: UUID, now: datetime) -> int:
        """Mark the team's pending invitations whose expiry has passed as expired."""
        ...

    async def list_for_recipient(
        self,
        recipient_id: UUID,
        *,
        status: InvitationStatus | None,
        limit: int,
        offset: int,
        now: datetime,
    ) -> TeamInvitationPage:
        """Lapsed pending invitations are listed, filtered and counted as expired."""
        ...

    async def list_for_team(
        self,
        team_id: UUID,
        *,
        status: InvitationStatus | None,
        limit: int,
        offset: int,
        now: datetime,
    ) -> TeamInvitationPage: ...

    async def count_pending(self, team_id: UUID, now: datetime) -> int:
        """Count unexpired sender submissions, independently of private delivery state."""
        ...
