"""Small read-only snapshots of enabled keyword collection configuration."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.direction import _plan_from_row
from ase.adapters.persistence.models import CollectionPlanRow
from ase.domain.collection import CollectionPlan

MAX_PLANS = 100


class SqlWatchlistPlanStore:
    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._session_factory = session_factory

    async def enabled_plans(self) -> list[CollectionPlan]:
        """Reload each poll, with a new session so edits and disablement are observed."""
        async with self._session_factory() as session:
            rows = await session.scalars(
                select(CollectionPlanRow)
                .where(CollectionPlanRow.enabled.is_(True))
                .order_by(CollectionPlanRow.created_at, CollectionPlanRow.id)
                .limit(MAX_PLANS)
            )
            return [_plan_from_row(row) for row in rows]
