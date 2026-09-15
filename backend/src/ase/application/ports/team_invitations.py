"""Persistence boundary for in-app team invitations."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from ase.domain.team_invitation import InvitationStatus, TeamInvitation, TeamInvitationPage


class DuplicateInvitation(Exception):
    """The recipient already holds a pending invitation to the team."""


class TeamInvitationRepository(Protocol):
    async def add(self, invitation: TeamInvitation) -> None: ...

    async def get(self, invitation_id: UUID) -> TeamInvitation | None: ...

    async def get_for_update(self, invitation_id: UUID) -> TeamInvitation | None: ...

    async def save(self, invitation: TeamInvitation) -> None: ...

    async def find_pending(self, team_id: UUID, recipient_id: UUID) -> TeamInvitation | None: ...

    async def list_for_recipient(
        self, recipient_id: UUID, *, status: InvitationStatus | None, limit: int, offset: int
    ) -> TeamInvitationPage: ...

    async def list_for_team(
        self, team_id: UUID, *, status: InvitationStatus | None, limit: int, offset: int
    ) -> TeamInvitationPage: ...

    async def count_pending(self, team_id: UUID) -> int: ...
