"""SQL for the bell: scoped unacknowledged alerts and each account's preferences."""

from __future__ import annotations

from collections.abc import Collection
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.access import visibility_predicate
from ase.adapters.persistence.bell_models import BellPreferenceRow, BellRuleMuteRow
from ase.adapters.persistence.models import AlertRow, IndicatorRow
from ase.adapters.persistence.warning_mapping import _alert_from_row
from ase.domain.access import Visibility
from ase.domain.bell import BellKind, BellPreferences, MutedRule
from ase.domain.warning import Alert


class SqlBellAlertQueries:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def unacknowledged(
        self,
        visibility: Visibility,
        since: datetime,
        muted_rules: Collection[UUID],
        limit: int,
    ) -> tuple[list[Alert], int]:
        conditions = [
            AlertRow.fired_at >= since,
            AlertRow.acknowledged_at.is_(None),
            visibility_predicate(AlertRow.created_by, AlertRow.team_id, visibility),
        ]
        if muted_rules:
            conditions.append(
                AlertRow.indicator_id.is_(None) | AlertRow.indicator_id.not_in(tuple(muted_rules))
            )
        total = await self._session.scalar(
            select(func.count()).select_from(AlertRow).where(*conditions)
        )
        rows = await self._session.scalars(
            select(AlertRow)
            .where(*conditions)
            .order_by(AlertRow.fired_at.desc(), AlertRow.id)
            .limit(limit)
            .execution_options(populate_existing=True)
        )
        return [_alert_from_row(row) for row in rows], int(total or 0)


def _kinds(values: object) -> frozenset[BellKind]:
    if not isinstance(values, list):
        return frozenset()
    return frozenset(BellKind(value) for value in values if value in set(BellKind))


class SqlBellPreferenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: UUID, visibility: Visibility) -> BellPreferences:
        row = await self._session.get(BellPreferenceRow, user_id, populate_existing=True)
        mutes = await self._session.execute(
            select(BellRuleMuteRow.indicator_id, IndicatorRow.name, BellRuleMuteRow.muted_at)
            .join(IndicatorRow, IndicatorRow.id == BellRuleMuteRow.indicator_id)
            .where(
                BellRuleMuteRow.user_id == user_id,
                visibility_predicate(IndicatorRow.created_by, IndicatorRow.team_id, visibility),
            )
            .order_by(IndicatorRow.name, BellRuleMuteRow.indicator_id)
        )
        return BellPreferences(
            user_id,
            _kinds(row.muted_kinds) if row is not None else frozenset(),
            tuple(MutedRule(rule_id, name, at) for rule_id, name, at in mutes),
        )

    async def muted_rule_ids(self, user_id: UUID) -> frozenset[UUID]:
        rows = await self._session.scalars(
            select(BellRuleMuteRow.indicator_id).where(BellRuleMuteRow.user_id == user_id)
        )
        return frozenset(rows)

    async def set_kinds(self, user_id: UUID, kinds: frozenset[BellKind], now: datetime) -> None:
        row = await self._session.get(BellPreferenceRow, user_id)
        values = sorted(kind.value for kind in kinds)
        if row is None:
            self._session.add(
                BellPreferenceRow(user_id=user_id, muted_kinds=values, updated_at=now)
            )
        else:
            row.muted_kinds = values
            row.updated_at = now
        await self._session.flush()

    async def count_rule_mutes(self, user_id: UUID) -> int:
        count = await self._session.scalar(
            select(func.count())
            .select_from(BellRuleMuteRow)
            .where(BellRuleMuteRow.user_id == user_id)
        )
        return int(count or 0)

    async def mute_rule(self, user_id: UUID, indicator_id: UUID, now: datetime) -> None:
        if await self._session.get(BellRuleMuteRow, (user_id, indicator_id)) is None:
            self._session.add(
                BellRuleMuteRow(user_id=user_id, indicator_id=indicator_id, muted_at=now)
            )
            await self._session.flush()

    async def unmute_rule(self, user_id: UUID, indicator_id: UUID) -> None:
        await self._session.execute(
            delete(BellRuleMuteRow).where(
                BellRuleMuteRow.user_id == user_id, BellRuleMuteRow.indicator_id == indicator_id
            )
        )
