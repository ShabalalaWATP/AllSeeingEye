"""Bounded resolution of AI reservations held as ``unknown`` after dispatch.

Rows are locked in the ledger's usual order: the call's reservation rows first, then
counters sorted by policy id. The observed monthly totals are not changed; the call
stays recorded there as an unknown request.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import func, select, update

from ase.adapters.persistence.ai_usage_mapping import rowcount
from ase.adapters.persistence.ai_usage_models import AiUsageCounterRow, AiUsageReservationRow
from ase.domain.ai_usage import AiCallOutcome, AiReservationStatus, charged_tokens

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

RESOLVED_UNKNOWN_ERROR = "resolved_unknown_after_bound"


class SqlAiUnknownResolution:
    if TYPE_CHECKING:
        _session: AsyncSession

    async def unknown_calls(self, before: datetime, limit: int) -> list[UUID]:
        """Calls with a reservation held as unknown since before ``before``, oldest first."""
        row = AiUsageReservationRow
        return list(
            await self._session.scalars(
                select(row.call_id)
                .where(row.status == AiReservationStatus.UNKNOWN.value, row.created_at < before)
                .group_by(row.call_id)
                .order_by(func.min(row.created_at))
                .limit(limit)
            )
        )

    async def resolve_unknown(self, call_id: UUID, now: datetime) -> bool:
        """Settle every unknown reservation of one call as a failed request.

        The request is counted once against each request limit. Tokens are charged only
        when the provider reported them, which for an unknown call is normally none, so
        the held worst-case token reservation returns to the allowance.
        """
        rows = list(
            await self._session.scalars(
                select(AiUsageReservationRow)
                .where(
                    AiUsageReservationRow.call_id == call_id,
                    AiUsageReservationRow.status == AiReservationStatus.UNKNOWN.value,
                )
                .order_by(AiUsageReservationRow.id)
                .execution_options(populate_existing=True)
            )
        )
        changed: list[tuple[AiUsageReservationRow, int]] = []
        for row in rows:
            actual = charged_tokens(
                AiCallOutcome.FAILED, row.prompt_tokens, row.completion_tokens, row.reserved_tokens
            )
            result = await self._session.execute(
                update(AiUsageReservationRow)
                .where(
                    AiUsageReservationRow.id == row.id,
                    AiUsageReservationRow.status == AiReservationStatus.UNKNOWN.value,
                )
                .values(
                    status=AiReservationStatus.SETTLED.value,
                    settled_at=now,
                    actual_tokens=actual,
                    ok=False,
                    error=RESOLVED_UNKNOWN_ERROR,
                )
            )
            if rowcount(result) == 1:
                changed.append((row, actual))
        counter = AiUsageCounterRow
        for row, actual in sorted(changed, key=lambda item: item[0].policy_id):
            result = await self._session.execute(
                update(counter)
                .where(
                    counter.policy_id == row.policy_id,
                    counter.period_start == row.period_start,
                    counter.reserved_requests >= 1,
                    counter.reserved_tokens >= row.reserved_tokens,
                )
                .values(
                    reserved_requests=counter.reserved_requests - 1,
                    reserved_tokens=counter.reserved_tokens - row.reserved_tokens,
                    used_requests=counter.used_requests + 1,
                    used_tokens=counter.used_tokens + actual,
                )
            )
            if rowcount(result) != 1:
                raise ValueError("AI usage counter is inconsistent with its reservation.")
        await self._session.flush()
        return bool(changed)
