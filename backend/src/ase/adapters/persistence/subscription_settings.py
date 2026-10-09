"""Conditional settings patch that never writes activation or execution history."""

from uuid import UUID

from sqlalchemy import JSON, ColumnElement, cast, func, literal, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.models import ScheduleRow
from ase.adapters.persistence.schedules import SqlScheduleRepository
from ase.domain.schedules import Schedule


class SqlSubscriptionSettings:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, subscription_id: UUID) -> Schedule | None:
        return await SqlScheduleRepository(self.session).get(subscription_id)

    async def update(self, expected: Schedule, edited: Schedule) -> Schedule | None:
        # JSON patching preserves fields concurrently changed by run bookkeeping.
        # Compare only editable configuration; pause/resume and runs are independent.
        values: dict[str, object] = {"name": edited.name}
        if expected.recurrence != edited.recurrence:
            options: ColumnElement[object]
            if self.session.get_bind().dialect.name == "sqlite":
                options = func.json_set(
                    func.coalesce(func.nullif(ScheduleRow.research_options, "null"), "{}"),
                    "$.monthday",
                    edited.monthday,
                    "$.anchor_month",
                    edited.anchor_month,
                )
            else:
                options = cast(
                    func.coalesce(
                        func.nullif(
                            cast(ScheduleRow.research_options, JSONB), literal(None, type_=JSONB)
                        ),
                        literal({}, type_=JSONB),
                    ).op("||")(
                        literal(
                            {"monthday": edited.monthday, "anchor_month": edited.anchor_month},
                            type_=JSONB,
                        )
                    ),
                    JSON,
                )
            values.update(
                timezone=edited.timezone,
                hour_utc=edited.hour_utc,
                local_hour=edited.local_hour,
                local_minute=edited.local_minute,
                cadence=edited.cadence,
                weekday=edited.weekday,
                research_options=options,
                next_run_at=edited.next_run_at,
            )
        changed = await self.session.scalar(
            update(ScheduleRow)
            .where(
                ScheduleRow.id == expected.id,
                ScheduleRow.created_by == expected.created_by,
                ScheduleRow.team_id == expected.team_id,
                ScheduleRow.brief_id == expected.brief_id,
                ScheduleRow.brief_revision == expected.brief_revision,
                ScheduleRow.archived_at.is_(None),
                ScheduleRow.name == expected.name,
                ScheduleRow.timezone == expected.timezone,
                ScheduleRow.local_hour == expected.local_hour,
                ScheduleRow.local_minute == expected.local_minute,
                ScheduleRow.cadence == expected.cadence,
                ScheduleRow.weekday == expected.weekday,
                func.coalesce(ScheduleRow.research_options["monthday"].as_integer(), 1)
                == expected.monthday,
                func.coalesce(ScheduleRow.research_options["anchor_month"].as_integer(), 1)
                == expected.anchor_month,
            )
            .values(**values)
            .returning(ScheduleRow.id)
            .execution_options(synchronize_session=False)
        )
        return await self.get(expected.id) if changed is not None else None
