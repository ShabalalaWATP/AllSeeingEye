"""The bell's fixed scope: the caller's own records and their current teams' records.

Administrators keep broad access elsewhere, but their bell never counts other people's
personal records or teams they have not joined (KAN-90's default ownership contract).
"""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from ase.application.access import AccessContext
from ase.application.ports.feeds import BusMessage, EventBus
from ase.domain.access import Visibility
from ase.domain.bell import BELL_CHANGED


def bell_visibility(access: AccessContext) -> Visibility:
    return Visibility(access.actor.id, False, tuple(access.memberships))


def in_bell_scope(access: AccessContext, created_by: UUID | None, team_id: UUID | None) -> bool:
    if team_id is None:
        return created_by is not None and created_by == access.actor.id
    return team_id in access.memberships


def can_acknowledge(access: AccessContext, team_id: UUID | None) -> bool:
    """Personal alerts in the bell are the caller's own; team alerts need an active team."""
    if team_id is None:
        return True
    team = access.teams.get(team_id)
    return team is not None and team.is_active and team_id in access.memberships


class BellSignals:
    """Content-free change signals, published only after the change has committed."""

    def __init__(self, bus: EventBus) -> None:
        self._bus = bus

    async def users(self, user_ids: Iterable[UUID]) -> None:
        targets = frozenset(user_ids)
        if targets:
            await self._bus.publish(BusMessage(BELL_CHANGED, {"user_ids": targets}))

    async def scope(self, created_by: UUID | None, team_id: UUID | None) -> None:
        """Everyone who can currently read records in this scope may need to refetch."""
        await self._bus.publish(BusMessage(BELL_CHANGED, {"scope": (created_by, team_id)}))
