"""Repositories for indicators and alerts, and the evaluator's own-session store."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence import alert_feedback
from ase.adapters.persistence.access import visibility_predicate
from ase.adapters.persistence.alert_reports import report_outcomes
from ase.adapters.persistence.models import (
    ActivitySampleRow,
    AlertRow,
    IndicatorRow,
)
from ase.adapters.persistence.warning_consumption_models import WarningConsumptionRow
from ase.adapters.persistence.warning_mapping import (
    _alert_from_row,
    _fill_indicator,
    _indicator_from_row,
)
from ase.adapters.persistence.warning_store import SqlWarningStore
from ase.domain.access import Visibility
from ase.domain.alert_feedback import AlertDisposition
from ase.domain.errors import NotFound
from ase.domain.indicator_baseline import matching_semantics
from ase.domain.warning import Alert, Indicator

__all__ = ["SqlAlertRepository", "SqlIndicatorRepository", "SqlWarningStore"]


class SqlIndicatorRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, indicator: Indicator) -> None:
        row = IndicatorRow(id=indicator.id)
        _fill_indicator(row, indicator)
        self._session.add(row)
        await self._session.flush()

    async def get(self, indicator_id: UUID) -> Indicator | None:
        row = await self._session.get(IndicatorRow, indicator_id, populate_existing=True)
        return None if row is None else _indicator_from_row(row)

    async def list_all(self, visibility: Visibility) -> list[Indicator]:
        rows = await self._session.scalars(
            select(IndicatorRow)
            .where(visibility_predicate(IndicatorRow.created_by, IndicatorRow.team_id, visibility))
            .order_by(IndicatorRow.name)
        )
        return [_indicator_from_row(row) for row in rows]

    async def save(self, indicator: Indicator) -> None:
        row = await self._session.get(IndicatorRow, indicator.id)
        if row is None:
            raise NotFound("Indicator not found.")
        if matching_semantics(_indicator_from_row(row)) != matching_semantics(indicator):
            await self._session.execute(
                delete(ActivitySampleRow).where(
                    ActivitySampleRow.kind == "indicator",
                    ActivitySampleRow.key == str(indicator.id),
                )
            )
        _fill_indicator(row, indicator)
        await self._session.flush()

    async def save_if_unchanged(self, indicator: Indicator, expected_updated_at: datetime) -> bool:
        before = await self.get(indicator.id)
        if before is None or before.updated_at != expected_updated_at:
            return False
        values = IndicatorRow(id=indicator.id)
        _fill_indicator(values, indicator)
        columns = {
            column.key: getattr(values, column.key)
            for column in IndicatorRow.__table__.columns
            if column.key not in {"id", "created_by", "created_at", "team_id"}
        }
        result = await self._session.execute(
            update(IndicatorRow)
            .where(
                IndicatorRow.id == indicator.id,
                IndicatorRow.updated_at == expected_updated_at,
            )
            .values(**columns)
            .execution_options(synchronize_session=False)
        )
        if getattr(result, "rowcount", 0) != 1:
            return False
        # Reset only the winning edit, under the same administration guard and transaction.
        if matching_semantics(before) != matching_semantics(indicator):
            await self._session.execute(
                delete(ActivitySampleRow).where(
                    ActivitySampleRow.kind == "indicator",
                    ActivitySampleRow.key == str(indicator.id),
                )
            )
        return True

    async def delete(self, indicator_id: UUID) -> None:
        # SQLite deployments may not enforce foreign-key cascades.
        await self._session.execute(
            delete(WarningConsumptionRow).where(WarningConsumptionRow.indicator_id == indicator_id)
        )
        await self._session.execute(delete(IndicatorRow).where(IndicatorRow.id == indicator_id))
        await self._session.flush()


class SqlAlertRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, alert_id: UUID) -> Alert | None:
        row = await self._session.get(AlertRow, alert_id, populate_existing=True)
        return (
            None
            if row is None
            else (await report_outcomes(self._session, [_alert_from_row(row)]))[0]
        )

    async def list_recent(self, since: datetime, limit: int, visibility: Visibility) -> list[Alert]:
        rows = await self._session.scalars(
            select(AlertRow)
            .where(
                AlertRow.fired_at >= since,
                visibility_predicate(AlertRow.created_by, AlertRow.team_id, visibility),
            )
            .order_by(AlertRow.fired_at.desc())
            .limit(limit)
        )
        return await report_outcomes(self._session, [_alert_from_row(row) for row in rows])

    async def save(self, alert: Alert) -> None:
        row = await self._session.get(AlertRow, alert.id)
        if row is None:
            raise NotFound("Alert not found.")
        row.acknowledged_at = alert.acknowledged_at
        row.acknowledged_by = alert.acknowledged_by
        row.report_id = alert.report_id
        await self._session.flush()

    async def acknowledge(self, alert: Alert) -> bool:
        return await alert_feedback.acknowledge(self._session, alert)

    async def feedback(
        self, indicator: Indicator, since: datetime, until: datetime
    ) -> dict[AlertDisposition, int]:
        return await alert_feedback.counts(
            self._session, indicator.id, indicator.created_by, indicator.team_id, since, until
        )
