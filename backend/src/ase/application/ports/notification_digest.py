"""Preference and durable progress boundary for daily digest scheduling."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from ase.domain.notification_digest import DigestPreferences


class DigestPreferenceRepository(Protocol):
    async def get(self, user_id: UUID) -> DigestPreferences: ...
    async def save(self, user_id: UUID, preferences: DigestPreferences, now: datetime) -> None: ...


class DigestSchedulerStore(Protocol):
    async def enqueue_due(self, now: datetime) -> int:
        """Create up to 100 unique daily intents and commit their progress together."""
        ...
