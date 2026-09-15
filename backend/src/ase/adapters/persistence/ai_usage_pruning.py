"""Bounded deletion of expired AI reservation, counter and totals rows.

Each method issues one ``DELETE ... WHERE key IN (SELECT key ... LIMIT n)`` so a run
removes at most ``limit`` rows on both SQLite and PostgreSQL. Callers own the
transaction and keep it short.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import delete, select, tuple_

from ase.adapters.persistence.ai_usage_mapping import rowcount
from ase.adapters.persistence.ai_usage_models import (
    AiUsageCounterRow,
    AiUsageReservationRow,
    AiUsageTotalRow,
)
from ase.domain.ai_usage import AiReservationStatus

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# Only finished reservations may go; ``reserved`` is in flight and ``unknown`` awaits review.
_PRUNABLE = (AiReservationStatus.RELEASED.value, AiReservationStatus.SETTLED.value)


class SqlAiUsagePruning:
    if TYPE_CHECKING:
        _session: AsyncSession

    async def prune_reservations(self, before: datetime, limit: int) -> int:
        """Delete finished reservations whose period ended before ``before``."""
        row = AiUsageReservationRow
        expired = (
            select(row.id)
            .where(row.status.in_(_PRUNABLE), row.period_end < before)
            .order_by(row.period_end, row.id)
            .limit(limit)
        )
        result = await self._session.execute(
            delete(row).where(row.id.in_(expired)).execution_options(synchronize_session=False)
        )
        return rowcount(result)

    async def prune_counters(self, before: datetime, limit: int) -> int:
        """Delete ended counters that no held reservation still depends on."""
        row = AiUsageCounterRow
        expired = (
            select(row.policy_id, row.period_start)
            .where(
                row.period_end < before,
                row.reserved_requests == 0,
                row.reserved_tokens == 0,
            )
            .order_by(row.period_end, row.policy_id)
            .limit(limit)
        )
        result = await self._session.execute(
            delete(row)
            .where(tuple_(row.policy_id, row.period_start).in_(expired))
            .execution_options(synchronize_session=False)
        )
        return rowcount(result)

    async def prune_totals(self, before: datetime, limit: int) -> int:
        """Delete monthly observation rows whose period ended before ``before``."""
        row = AiUsageTotalRow
        expired = (
            select(row.period_start, row.team_key, row.user_key)
            # period_start is implied by period_end and lets the primary key serve the range.
            .where(row.period_start < before, row.period_end < before)
            .order_by(row.period_start, row.team_key, row.user_key)
            .limit(limit)
        )
        result = await self._session.execute(
            delete(row)
            .where(tuple_(row.period_start, row.team_key, row.user_key).in_(expired))
            .execution_options(synchronize_session=False)
        )
        return rowcount(result)
