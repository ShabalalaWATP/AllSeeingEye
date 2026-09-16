"""Read bounded monthly AI usage observations for accounts, teams and system work."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import func, select

from ase.adapters.persistence.ai_usage_models import NIL_KEY, AiUsageTotalRow
from ase.adapters.persistence.models import UserRow
from ase.domain.ai_usage import AiAllowancePeriod, AiMemberUsage, AiUsageTotals, period_bounds

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

MAX_MEMBER_ROWS = 200


class SqlAiTotalsReader:
    if TYPE_CHECKING:
        _session: AsyncSession

    async def _sum(self, now: datetime, *conditions: Any) -> AiUsageTotals:
        start, end = period_bounds(now, AiAllowancePeriod.MONTH)
        row = (
            await self._session.execute(
                select(
                    func.coalesce(func.sum(AiUsageTotalRow.used_requests), 0),
                    func.coalesce(func.sum(AiUsageTotalRow.used_tokens), 0),
                    func.coalesce(func.sum(AiUsageTotalRow.unknown_requests), 0),
                    func.coalesce(func.sum(AiUsageTotalRow.used_input_tokens), 0),
                    func.coalesce(func.sum(AiUsageTotalRow.used_output_tokens), 0),
                ).where(AiUsageTotalRow.period_start == start, *conditions)
            )
        ).one()
        return AiUsageTotals(
            start, end, int(row[0]), int(row[1]), int(row[2]), int(row[3]), int(row[4])
        )

    async def account_totals(self, user_id: UUID, now: datetime) -> AiUsageTotals:
        """Everything this account initiated, personal and for any team."""
        return await self._sum(now, AiUsageTotalRow.user_key == user_id)

    async def team_totals(
        self, team_id: UUID, now: datetime, *, user_id: UUID | None = None
    ) -> AiUsageTotals:
        conditions = [AiUsageTotalRow.team_key == team_id]
        if user_id is not None:
            conditions.append(AiUsageTotalRow.user_key == user_id)
        return await self._sum(now, *conditions)

    async def site_totals(self, now: datetime) -> AiUsageTotals:
        """Everything recorded this month: personal, team and system work together."""
        return await self._sum(now)

    async def system_totals(self, now: datetime) -> AiUsageTotals:
        return await self._sum(
            now, AiUsageTotalRow.team_key == NIL_KEY, AiUsageTotalRow.user_key == NIL_KEY
        )

    async def team_member_totals(self, team_id: UUID, now: datetime) -> list[AiMemberUsage]:
        start, end = period_bounds(now, AiAllowancePeriod.MONTH)
        rows = await self._session.execute(
            select(AiUsageTotalRow, UserRow.display_name)
            .join(UserRow, UserRow.id == AiUsageTotalRow.user_key)
            .where(AiUsageTotalRow.period_start == start, AiUsageTotalRow.team_key == team_id)
            .order_by(AiUsageTotalRow.used_tokens.desc(), UserRow.display_name)
            .limit(MAX_MEMBER_ROWS)
        )
        return [
            AiMemberUsage(
                total.user_key,
                name,
                AiUsageTotals(
                    start,
                    end,
                    total.used_requests,
                    total.used_tokens,
                    total.unknown_requests,
                    total.used_input_tokens,
                    total.used_output_tokens,
                ),
            )
            for total, name in rows.tuples()
        ]
