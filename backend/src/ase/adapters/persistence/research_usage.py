"""SQL implementation of research counters; mutations require the shared user guard."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.research_usage_models import ResearchTierRow, ResearchUsageRow
from ase.domain.research_usage import ResearchPeriod


class SqlResearchUsageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def assignment(self, user_id: UUID) -> tuple[int, int]:
        row = await self._session.get(ResearchTierRow, user_id, populate_existing=True)
        return (row.tier, row.revision) if row else (1, 0)

    async def assign(self, user_id: UUID, tier: int, revision: int) -> None:
        row = await self._session.get(ResearchTierRow, user_id, populate_existing=True)
        if row is None:
            self._session.add(ResearchTierRow(user_id=user_id, tier=tier, revision=revision))
        else:
            row.tier, row.revision = tier, revision
        await self._session.flush()

    async def used(self, user_id: UUID, period: ResearchPeriod, start: datetime) -> int:
        row = await self._session.get(
            ResearchUsageRow, (user_id, period, start), populate_existing=True
        )
        return row.used if row else 0

    async def increment(self, user_id: UUID, period: ResearchPeriod, start: datetime) -> None:
        # Only the current calendar bucket matters. Retain at most one of each period.
        await self._session.execute(
            delete(ResearchUsageRow).where(
                ResearchUsageRow.user_id == user_id,
                ResearchUsageRow.period == period,
                ResearchUsageRow.period_start < start,
            )
        )
        row = await self._session.get(
            ResearchUsageRow, (user_id, period, start), populate_existing=True
        )
        if row is None:
            self._session.add(
                ResearchUsageRow(user_id=user_id, period=period, period_start=start, used=1)
            )
        else:
            row.used += 1
        await self._session.flush()
