"""Atomic edits to the small mutable surface of a pinned subscription."""

from typing import Protocol
from uuid import UUID

from ase.domain.schedules import Schedule


class SubscriptionSettingsStore(Protocol):
    async def get(self, subscription_id: UUID) -> Schedule | None: ...
    async def update(self, expected: Schedule, edited: Schedule) -> Schedule | None:
        """Compare settings and patch only name/recurrence, retaining current run state."""
        ...
