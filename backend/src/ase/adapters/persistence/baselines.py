"""Hourly activity samples: the one durable table that grows with time, a few rows an hour."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.models import ActivitySampleRow


class SqlBaselineRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(self, kind: str, key: str, hour: datetime, value: int) -> None:
        row = (
            await self._session.scalars(
                select(ActivitySampleRow).where(
                    ActivitySampleRow.kind == kind,
                    ActivitySampleRow.key == key,
                    ActivitySampleRow.hour == hour,
                )
            )
        ).first()
        if row is None:
            self._session.add(ActivitySampleRow(kind=kind, key=key, hour=hour, value=value))
        elif value > row.value:
            row.value = value
        await self._session.flush()

    async def means(self, kind: str, since: datetime) -> Mapping[str, float]:
        rows = await self._session.execute(
            select(ActivitySampleRow.key, func.avg(ActivitySampleRow.value))
            .where(ActivitySampleRow.kind == kind, ActivitySampleRow.hour >= since)
            .group_by(ActivitySampleRow.key)
        )
        return {str(key): float(mean) for key, mean in rows.all()}


class SqlBaselineSink:
    """Opens its own session per batch, so a background sampler never shares one."""

    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._session_factory = session_factory

    async def record_many(self, hour: datetime, samples: Sequence[tuple[str, str, int]]) -> None:
        async with self._session_factory() as session:
            repository = SqlBaselineRepository(session)
            for kind, key, value in samples:
                await repository.record(kind, key, hour, value)
            await session.commit()
