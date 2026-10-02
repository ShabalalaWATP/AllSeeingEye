"""Session-isolated baseline reads and samples for one standing rule."""

from collections.abc import Callable
from datetime import datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.baselines import SqlBaselineRepository
from ase.adapters.persistence.models import ActivitySampleRow, IndicatorRow
from ase.adapters.persistence.warning_mapping import _indicator_from_row
from ase.application.access import AccessPolicy
from ase.domain.errors import Forbidden, Unauthenticated
from ase.domain.indicator_baseline import IndicatorBaseline
from ase.domain.warning import Indicator


async def summary(session: AsyncSession, rule: Indicator, now: datetime) -> IndicatorBaseline:
    hour = now.replace(minute=0, second=0, microsecond=0)
    row = (
        await session.execute(
            select(
                func.count(), func.avg(ActivitySampleRow.value), func.min(ActivitySampleRow.hour)
            ).where(
                ActivitySampleRow.kind == "indicator",
                ActivitySampleRow.key == str(rule.id),
                ActivitySampleRow.hour >= hour - timedelta(days=rule.baseline_days),
                ActivitySampleRow.hour < hour,
            )
        )
    ).one()
    return IndicatorBaseline(
        int(row[0]), float(row[1]) if row[1] is not None else None, row[2], hour
    )


class SqlIndicatorBaselines:
    def __init__(
        self, sessions: Callable[[], AsyncSession], policy: Callable[[AsyncSession], AccessPolicy]
    ) -> None:
        self.sessions, self.policy = sessions, policy

    async def summary(self, rule: Indicator, now: datetime) -> IndicatorBaseline:
        async with self.sessions() as session:
            return await summary(session, rule, now)

    async def record(self, rule: Indicator, hour: datetime, count: int) -> None:
        async with self.sessions() as session:
            try:
                await self.policy(session).background(
                    rule.created_by, rule.team_id, for_update=True
                )
            except (Forbidden, Unauthenticated):
                return
            current = await session.get(IndicatorRow, rule.id, populate_existing=True)
            if current is None or _indicator_from_row(current) != rule:
                return
            # The same guard as edits prevents an old-semantics sample after a reset.
            await SqlBaselineRepository(session).record("indicator", str(rule.id), hour, count)
            await session.execute(
                delete(ActivitySampleRow).where(
                    ActivitySampleRow.kind == "indicator",
                    ActivitySampleRow.hour < hour - timedelta(days=30),
                )
            )
            await session.commit()
