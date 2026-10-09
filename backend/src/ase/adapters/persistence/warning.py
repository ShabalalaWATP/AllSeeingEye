"""Repositories for indicators and alerts, and the evaluator's own-session store."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import ScalarResult, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence import alert_feedback
from ase.adapters.persistence.access import visibility_predicate
from ase.adapters.persistence.alert_notification_enqueue import enqueue_alert_notifications
from ase.adapters.persistence.models import (
    ActivitySampleRow,
    AlertRow,
    CollectionPlanRow,
    IndicatorRow,
    ReportRow,
)
from ase.adapters.persistence.warning_mapping import (
    _alert_from_row,
    _alert_row,
    _fill_indicator,
    _indicator_from_row,
)
from ase.application.access import AccessContext, AccessPolicy
from ase.domain.access import Visibility
from ase.domain.alert_feedback import AlertDisposition
from ase.domain.errors import Forbidden, InvalidRequest, NotFound, Unauthenticated
from ase.domain.indicator_baseline import matching_semantics
from ase.domain.warning import Alert, Indicator


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
        await self._session.execute(delete(IndicatorRow).where(IndicatorRow.id == indicator_id))
        await self._session.flush()


class SqlAlertRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, alert_id: UUID) -> Alert | None:
        row = await self._session.get(AlertRow, alert_id, populate_existing=True)
        return None if row is None else _alert_from_row(row)

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
        return [_alert_from_row(row) for row in rows]

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


class SqlWarningStore:
    """Opens its own session per call, so the evaluator never shares one with a request."""

    def __init__(
        self,
        session_factory: Callable[[], AsyncSession],
        policy_factory: Callable[[AsyncSession], AccessPolicy],
        *,
        installation_copy: bool = False,
    ) -> None:
        self._session_factory = session_factory
        self._policy_factory = policy_factory
        self._installation_copy = installation_copy

    async def _authorise(
        self, session: AsyncSession, row: IndicatorRow, *, for_update: bool = False
    ) -> AccessContext | None:
        origin = (row.created_by, row.team_id)
        try:
            access = await self._policy_factory(session).background(
                row.created_by, row.team_id, for_update=for_update
            )
            current = await session.get(IndicatorRow, row.id, populate_existing=True)
            if current is None:
                return None
            if not row.enabled or (row.created_by, row.team_id) != origin:
                return None
            if row.plan_id is not None:
                plan = await session.get(CollectionPlanRow, row.plan_id, populate_existing=True)
                if plan is None:
                    return None
                access.require_same_scope(
                    row.created_by, row.team_id, plan.created_by, plan.team_id
                )
            return access
        except (Forbidden, InvalidRequest, NotFound, Unauthenticated):
            return None

    async def can_run(self, indicator: Indicator) -> bool:
        async with self._session_factory() as session:
            row = await session.get(IndicatorRow, indicator.id)
            if row is None or await self._authorise(session, row) is None:
                return False
            return _indicator_from_row(row) == indicator

    async def enabled_indicators(self) -> list[Indicator]:
        async with self._session_factory() as session:
            rows = await session.scalars(select(IndicatorRow).where(IndicatorRow.enabled.is_(True)))
            return [_indicator_from_row(row) for row in rows]

    async def latest_alert(self, indicator_id: UUID) -> Alert | None:
        async with self._session_factory() as session:
            row = await session.scalar(
                select(AlertRow)
                .where(AlertRow.indicator_id == indicator_id)
                .order_by(AlertRow.fired_at.desc())
                .limit(1)
            )
            return None if row is None else _alert_from_row(row)

    async def alerted_event_ids(self, indicator_id: UUID, since: datetime) -> frozenset[str]:
        # Both predicates run in SQL; only the cited ids column is loaded, with no limit,
        # so an older alert inside the window can never be dropped and re-fire.
        async with self._session_factory() as session:
            cited: ScalarResult[list[Any]] = await session.scalars(
                select(AlertRow.event_ids).where(
                    AlertRow.indicator_id == indicator_id, AlertRow.fired_at >= since
                )
            )
            return frozenset(str(item) for ids in cited for item in ids or ())

    async def add_alert(self, alert: Alert, indicator: Indicator) -> bool:
        if (
            alert.report_id is not None
            or alert.indicator_id is None
            or alert.schedule_id is not None
        ):
            return False  # Reports are linked only through the separately authorised path.
        async with self._session_factory() as session:
            row = await session.get(IndicatorRow, alert.indicator_id)
            if row is None or await self._authorise(session, row, for_update=True) is None:
                return False
            if (alert.created_by, alert.team_id) != (row.created_by, row.team_id):
                return False
            if _indicator_from_row(row) != indicator:
                return False
            latest = await session.scalar(
                select(AlertRow)
                .where(AlertRow.indicator_id == row.id)
                .order_by(AlertRow.fired_at.desc())
                .limit(1)
            )
            if latest is not None and alert.fired_at - latest.fired_at < indicator.cooldown:
                return False
            session.add(_alert_row(alert))
            await session.flush()
            await enqueue_alert_notifications(
                session, alert, installation_copy=self._installation_copy
            )
            await session.commit()
            return True

    async def attach_report(self, alert_id: UUID, report_id: UUID) -> bool:
        async with self._session_factory() as session:
            row = await session.get(AlertRow, alert_id)
            indicator = (
                None
                if row is None or row.indicator_id is None
                else await session.get(IndicatorRow, row.indicator_id)
            )
            if row is None or indicator is None:
                return False
            access = await self._authorise(session, indicator, for_update=True)
            row = await session.get(AlertRow, alert_id, populate_existing=True)
            if row is None:
                return False
            if access is None or (row.created_by, row.team_id) != (
                indicator.created_by,
                indicator.team_id,
            ):
                return False
            report = await session.get(ReportRow, report_id, populate_existing=True)
            if report is None:
                return False
            try:
                access.require_same_scope(
                    row.created_by, row.team_id, report.created_by, report.team_id
                )
            except (Forbidden, InvalidRequest, NotFound):
                return False
            row.report_id = report_id
            await session.commit()
            return True

    async def prune(self, before: datetime) -> int:
        async with self._session_factory() as session:
            stale = select(func.count()).select_from(AlertRow).where(AlertRow.fired_at < before)
            count = int(await session.scalar(stale) or 0)
            if count:
                await session.execute(delete(AlertRow).where(AlertRow.fired_at < before))
            # Counts use acknowledgement days, not the raw alert's firing time.
            cutoff = before.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            await alert_feedback.prune(session, cutoff)
            await session.commit()
            return count
