"""Repositories for indicators and alerts, and the evaluator's own-session store."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.models import AlertRow, IndicatorRow
from ase.domain.errors import NotFound
from ase.domain.events import BoundingBox, Category
from ase.domain.warning import Alert, Indicator


def _indicator_from_row(row: IndicatorRow) -> Indicator:
    bbox = None
    edges = (row.west, row.south, row.east, row.north)
    if all(edge is not None for edge in edges):
        bbox = BoundingBox(west=edges[0], south=edges[1], east=edges[2], north=edges[3])  # type: ignore[arg-type]
    return Indicator(
        id=row.id,
        name=row.name,
        description=row.description,
        plan_id=row.plan_id,
        countries=tuple(str(code) for code in row.countries),
        bbox=bbox,
        categories=tuple(Category(str(value)) for value in row.categories),
        keywords=tuple(str(word) for word in row.keywords),
        threshold=row.threshold,
        window_minutes=row.window_minutes,
        cooldown_minutes=row.cooldown_minutes,
        severity_floor=row.severity_floor,
        report_template=row.report_template,
        enabled=row.enabled,
        created_by=row.created_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _fill_indicator(row: IndicatorRow, indicator: Indicator) -> None:
    row.name = indicator.name
    row.description = indicator.description
    row.plan_id = indicator.plan_id
    row.countries = list(indicator.countries)
    row.west = indicator.bbox.west if indicator.bbox else None
    row.south = indicator.bbox.south if indicator.bbox else None
    row.east = indicator.bbox.east if indicator.bbox else None
    row.north = indicator.bbox.north if indicator.bbox else None
    row.categories = [category.value for category in indicator.categories]
    row.keywords = list(indicator.keywords)
    row.threshold = indicator.threshold
    row.window_minutes = indicator.window_minutes
    row.cooldown_minutes = indicator.cooldown_minutes
    row.severity_floor = indicator.severity_floor
    row.report_template = indicator.report_template
    row.enabled = indicator.enabled
    row.created_by = indicator.created_by
    row.created_at = indicator.created_at
    row.updated_at = indicator.updated_at


def _alert_from_row(row: AlertRow) -> Alert:
    return Alert(
        id=row.id,
        indicator_id=row.indicator_id,
        fired_at=row.fired_at,
        title=row.title,
        summary=row.summary,
        count=row.count,
        threshold=row.threshold,
        event_ids=tuple(str(item) for item in row.event_ids),
        countries=tuple(str(code) for code in row.countries),
        acknowledged_at=row.acknowledged_at,
        acknowledged_by=row.acknowledged_by,
        report_id=row.report_id,
    )


def _alert_row(alert: Alert) -> AlertRow:
    return AlertRow(
        id=alert.id,
        indicator_id=alert.indicator_id,
        fired_at=alert.fired_at,
        title=alert.title,
        summary=alert.summary,
        count=alert.count,
        threshold=alert.threshold,
        event_ids=list(alert.event_ids),
        countries=list(alert.countries),
        acknowledged_at=alert.acknowledged_at,
        acknowledged_by=alert.acknowledged_by,
        report_id=alert.report_id,
    )


class SqlIndicatorRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, indicator: Indicator) -> None:
        row = IndicatorRow(id=indicator.id)
        _fill_indicator(row, indicator)
        self._session.add(row)
        await self._session.flush()

    async def get(self, indicator_id: UUID) -> Indicator | None:
        row = await self._session.get(IndicatorRow, indicator_id)
        return None if row is None else _indicator_from_row(row)

    async def list_all(self) -> list[Indicator]:
        rows = await self._session.scalars(select(IndicatorRow).order_by(IndicatorRow.name))
        return [_indicator_from_row(row) for row in rows]

    async def save(self, indicator: Indicator) -> None:
        row = await self._session.get(IndicatorRow, indicator.id)
        if row is None:
            raise NotFound("Indicator not found.")
        _fill_indicator(row, indicator)
        await self._session.flush()

    async def delete(self, indicator_id: UUID) -> None:
        await self._session.execute(delete(IndicatorRow).where(IndicatorRow.id == indicator_id))
        await self._session.flush()


class SqlAlertRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, alert_id: UUID) -> Alert | None:
        row = await self._session.get(AlertRow, alert_id)
        return None if row is None else _alert_from_row(row)

    async def list_recent(self, since: datetime, limit: int) -> list[Alert]:
        rows = await self._session.scalars(
            select(AlertRow)
            .where(AlertRow.fired_at >= since)
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


class SqlWarningStore:
    """Opens its own session per call, so the evaluator never shares one with a request."""

    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._session_factory = session_factory

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

    async def add_alert(self, alert: Alert) -> None:
        async with self._session_factory() as session:
            session.add(_alert_row(alert))
            await session.commit()

    async def attach_report(self, alert_id: UUID, report_id: UUID) -> None:
        async with self._session_factory() as session:
            row = await session.get(AlertRow, alert_id)
            if row is not None:
                row.report_id = report_id
                await session.commit()

    async def prune(self, before: datetime) -> int:
        async with self._session_factory() as session:
            stale = select(func.count()).select_from(AlertRow).where(AlertRow.fired_at < before)
            count = int(await session.scalar(stale) or 0)
            if count:
                await session.execute(delete(AlertRow).where(AlertRow.fired_at < before))
                await session.commit()
            return count
