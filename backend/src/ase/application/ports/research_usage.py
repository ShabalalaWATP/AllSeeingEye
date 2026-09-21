"""Persistent research assignments and counters, independent of report retention."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from ase.domain.research_usage import ResearchPeriod


class ResearchUsageRepository(Protocol):
    async def assignment(self, user_id: UUID) -> tuple[int, int]:
        """Return (tier, revision), defaulting to (1, 0) without inserting a row."""
        ...

    async def assign(self, user_id: UUID, tier: int, revision: int) -> None: ...

    async def used(self, user_id: UUID, period: ResearchPeriod, start: datetime) -> int: ...

    async def increment(self, user_id: UUID, period: ResearchPeriod, start: datetime) -> None:
        """Caller owns the administration/account locks and surrounding transaction."""
        ...
