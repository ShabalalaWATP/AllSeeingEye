"""Repositories for scheduled products and the runner's own-session store."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.models import ScheduleRow
from ase.domain.errors import NotFound
from ase.domain.schedules import Schedule


def _from_row(row: ScheduleRow) -> Schedule:
    return Schedule(
        id=row.id,
        name=row.name,
        template_id=row.template_id,
        country_iso=row.country_iso,
        plan_id=row.plan_id,
        hour_utc=row.hour_utc,
        cadence=row.cadence,
        weekday=row.weekday,
        window_hours=row.window_hours,
        enabled=row.enabled,
        created_by=row.created_by,
        created_at=row.created_at,
        next_run_at=row.next_run_at,
        last_run_at=row.last_run_at,
        last_report_id=row.last_report_id,
        last_error=row.last_error,
    )


def _fill(row: ScheduleRow, schedule: Schedule) -> None:
    row.name = schedule.name
    row.template_id = schedule.template_id
    row.country_iso = schedule.country_iso
    row.plan_id = schedule.plan_id
    row.hour_utc = schedule.hour_utc
    row.cadence = schedule.cadence
    row.weekday = schedule.weekday
    row.window_hours = schedule.window_hours
    row.enabled = schedule.enabled
    row.created_by = schedule.created_by
    row.created_at = schedule.created_at
    row.next_run_at = schedule.next_run_at
    row.last_run_at = schedule.last_run_at
    row.last_report_id = schedule.last_report_id
    row.last_error = schedule.last_error


class SqlScheduleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, schedule: Schedule) -> None:
        row = ScheduleRow(id=schedule.id)
        _fill(row, schedule)
        self._session.add(row)
        await self._session.flush()

    async def get(self, schedule_id: UUID) -> Schedule | None:
        row = await self._session.get(ScheduleRow, schedule_id)
        return None if row is None else _from_row(row)

    async def list_all(self) -> list[Schedule]:
        rows = await self._session.scalars(select(ScheduleRow).order_by(ScheduleRow.name))
        return [_from_row(row) for row in rows]

    async def save(self, schedule: Schedule) -> None:
        row = await self._session.get(ScheduleRow, schedule.id)
        if row is None:
            raise NotFound("Schedule not found.")
        _fill(row, schedule)
        await self._session.flush()

    async def delete(self, schedule_id: UUID) -> None:
        await self._session.execute(delete(ScheduleRow).where(ScheduleRow.id == schedule_id))
        await self._session.flush()


class SqlScheduleStore:
    """Opens its own session per call, so the runner never shares one with a request."""

    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._session_factory = session_factory

    async def due(self, now: datetime) -> list[Schedule]:
        async with self._session_factory() as session:
            rows = await session.scalars(
                select(ScheduleRow)
                .where(ScheduleRow.enabled.is_(True), ScheduleRow.next_run_at <= now)
                .order_by(ScheduleRow.next_run_at)
            )
            return [_from_row(row) for row in rows]

    async def mark_run(
        self,
        schedule_id: UUID,
        *,
        ran_at: datetime,
        next_run_at: datetime,
        report_id: UUID | None,
        error: str | None,
    ) -> None:
        async with self._session_factory() as session:
            row = await session.get(ScheduleRow, schedule_id)
            if row is None:
                return
            row.last_run_at = ran_at
            row.next_run_at = next_run_at
            row.last_error = error
            if report_id is not None:
                row.last_report_id = report_id
            await session.commit()
