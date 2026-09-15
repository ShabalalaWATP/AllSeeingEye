"""Transactional edition ledger with database uniqueness and optimistic fences."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.operational_models import ScheduleRow
from ase.adapters.persistence.subscription_due_selection import due_edition_rows
from ase.adapters.persistence.subscription_edition_codec import (
    attempt_from_row,
    attempt_values,
    delivery_from_row,
    delivery_values,
    edition_from_row,
    edition_values,
    lineage_from_row,
    lineage_values,
    revision_from_row,
    revision_values,
)
from ase.adapters.persistence.subscription_edition_models import (
    SubscriptionAttemptRow,
    SubscriptionDeliveryRow,
    SubscriptionEditionRow,
    SubscriptionLineageRow,
    SubscriptionRevisionRow,
)
from ase.application.schedules.runner import DueCursor
from ase.domain.errors import Conflict, NotFound
from ase.domain.subscription_editions import (
    ACTIVE_WORKFLOWS,
    EditionAttempt,
    EditionDelivery,
    EditionTrigger,
    EditionWorkflow,
    SubscriptionEdition,
    SubscriptionLineage,
    SubscriptionRevision,
)


def _page(limit: int, offset: int = 0) -> None:
    if type(limit) is not int or not 1 <= limit <= 100 or type(offset) is not int or offset < 0:
        raise ValueError("Use a bounded subscription history page.")


class SqlSubscriptionEditionRepository:
    """Never commits: admission and the report job must share their caller's transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _insert_once(self, table: type[Any], values: dict[str, object]) -> None:
        dialect = self.session.get_bind().dialect.name
        if dialect == "sqlite":
            await self.session.execute(
                sqlite_insert(table).values(**values).on_conflict_do_nothing()
            )
        elif dialect == "postgresql":
            await self.session.execute(pg_insert(table).values(**values).on_conflict_do_nothing())
        else:
            raise RuntimeError("Subscription editions require SQLite or PostgreSQL.")

    async def add_revision(self, revision: SubscriptionRevision) -> SubscriptionRevision:
        schedule = await self.session.get(ScheduleRow, revision.subscription_id)
        if schedule is None:
            raise NotFound("Subscription not found.")
        if (schedule.created_by, schedule.team_id) != (revision.owner_id, revision.team_id):
            raise Conflict("Subscription revision scope does not match its owner.")
        await self._insert_once(SubscriptionRevisionRow, revision_values(revision))
        stored = await self.get_revision(revision.subscription_id, revision.revision)
        if stored != revision:
            raise Conflict("A different immutable subscription revision already exists.")
        return stored

    async def get_revision(
        self, subscription_id: UUID, revision: int
    ) -> SubscriptionRevision | None:
        row = await self.session.get(
            SubscriptionRevisionRow, (subscription_id, revision), populate_existing=True
        )
        return revision_from_row(row) if row is not None else None

    async def latest_revision(self, subscription_id: UUID) -> SubscriptionRevision | None:
        row = await self.session.scalar(
            select(SubscriptionRevisionRow)
            .where(SubscriptionRevisionRow.subscription_id == subscription_id)
            .order_by(SubscriptionRevisionRow.revision.desc())
            .limit(1)
            .execution_options(populate_existing=True)
        )
        return revision_from_row(row) if row is not None else None

    async def reserve(self, edition: SubscriptionEdition) -> SubscriptionEdition:
        if (
            edition.workflow is not EditionWorkflow.PENDING
            or edition.revision != 1
            or edition.job_id is not None
            or edition.report_id is not None
        ):
            raise ValueError("Reserve an unstarted pending edition before any provider work.")
        revision = await self.get_revision(edition.subscription_id, edition.frozen_revision)
        if revision is None or not revision.enabled:
            raise Conflict("The frozen subscription revision is unavailable or disabled.")
        if revision.compatibility_fingerprint != edition.compatibility_fingerprint:
            raise Conflict("Edition compatibility does not match its frozen revision.")
        await self._insert_once(SubscriptionEditionRow, edition_values(edition))
        stored = await self.get_by_identity(edition)
        if stored is None:
            raise Conflict("Another active edition already holds this subscription.")
        if stored.logical_payload != edition.logical_payload or (
            stored.workflow is EditionWorkflow.PENDING
            and (stored.effective_intervals, stored.gaps)
            != (edition.effective_intervals, edition.gaps)
        ):
            raise Conflict("A logical edition key was reused with different frozen inputs.")
        return stored

    async def get_by_identity(self, edition: SubscriptionEdition) -> SubscriptionEdition | None:
        predicate: tuple[ColumnElement[bool], ...]
        if edition.trigger in (EditionTrigger.SCHEDULED, EditionTrigger.CATCH_UP):
            predicate = (
                SubscriptionEditionRow.subscription_id == edition.subscription_id,
                SubscriptionEditionRow.due_at_utc == edition.due_at_utc,
            )
        else:
            predicate = (
                SubscriptionEditionRow.subscription_id == edition.subscription_id,
                SubscriptionEditionRow.trigger == edition.trigger.value,
                SubscriptionEditionRow.request_uuid == edition.request_uuid,
            )
        row = await self.session.scalar(
            select(SubscriptionEditionRow)
            .where(*predicate)
            .execution_options(populate_existing=True)
        )
        return edition_from_row(row) if row is not None else None

    async def get(self, edition_id: UUID) -> SubscriptionEdition | None:
        row = await self.session.get(SubscriptionEditionRow, edition_id, populate_existing=True)
        return edition_from_row(row) if row is not None else None

    async def get_by_job(self, job_id: UUID) -> SubscriptionEdition | None:
        row = await self.session.scalar(
            select(SubscriptionEditionRow)
            .where(SubscriptionEditionRow.job_id == job_id)
            .execution_options(populate_existing=True)
        )
        return edition_from_row(row) if row is not None else None

    async def get_by_version(self, version_id: UUID) -> SubscriptionEdition | None:
        row = await self.session.scalar(
            select(SubscriptionEditionRow)
            .where(SubscriptionEditionRow.version_id == version_id)
            .execution_options(populate_existing=True)
        )
        return edition_from_row(row) if row is not None else None

    async def active(self, subscription_id: UUID) -> SubscriptionEdition | None:
        row = await self.session.scalar(
            select(SubscriptionEditionRow)
            .where(
                SubscriptionEditionRow.subscription_id == subscription_id,
                SubscriptionEditionRow.workflow.in_(tuple(item.value for item in ACTIVE_WORKFLOWS)),
            )
            .execution_options(populate_existing=True)
        )
        return edition_from_row(row) if row is not None else None

    async def due(self, now: datetime, limit: int = 50) -> list[SubscriptionEdition]:
        rows, _ = await self.due_batch(now, limit=limit)
        return [edition for edition, _ in rows]

    async def due_batch(
        self, now: datetime, *, limit: int = 16, cursor: DueCursor | None = None
    ) -> tuple[list[tuple[SubscriptionEdition, UUID]], DueCursor | None]:
        rows, next_cursor = await due_edition_rows(self.session, now, limit=limit, cursor=cursor)
        return [(edition_from_row(row), owner) for row, owner in rows], next_cursor

    async def history(
        self, subscription_id: UUID, *, limit: int = 50, offset: int = 0
    ) -> list[SubscriptionEdition]:
        _page(limit, offset)
        rows = await self.session.scalars(
            select(SubscriptionEditionRow)
            .where(SubscriptionEditionRow.subscription_id == subscription_id)
            .order_by(SubscriptionEditionRow.created_at.desc(), SubscriptionEditionRow.id)
            .limit(limit)
            .offset(offset)
        )
        return [edition_from_row(row) for row in rows]

    async def advance(
        self, edition: SubscriptionEdition, *, expected_revision: int
    ) -> SubscriptionEdition | None:
        previous = await self.get(edition.id)
        if previous is None:
            return None
        if (
            previous.logical_payload != edition.logical_payload
            or previous.created_at != edition.created_at
            or edition.revision != expected_revision + 1
            or edition.updated_at < previous.updated_at
            or (previous.job_id is not None and previous.job_id != edition.job_id)
            or (previous.version_id is not None and previous.version_id != edition.version_id)
            or (
                previous.covered_by_edition_id is not None
                and previous.covered_by_edition_id != edition.covered_by_edition_id
            )
            or (previous.accepted_as_baseline and not edition.accepted_as_baseline)
        ):
            raise Conflict("An edition update cannot rewrite frozen inputs or saved links.")
        values = edition_values(edition)
        mutable = {
            key: values[key]
            for key in (
                "workflow",
                "report_quality",
                "coverage",
                "effective_intervals",
                "gaps",
                "updated_at",
                "revision",
                "job_id",
                "report_id",
                "version_id",
                "safe_reason",
                "covered_by_edition_id",
                "accepted_as_baseline",
            )
        }
        updated = await self.session.scalar(
            update(SubscriptionEditionRow)
            .where(
                SubscriptionEditionRow.id == edition.id,
                SubscriptionEditionRow.revision == expected_revision,
            )
            .values(**mutable)
            .returning(SubscriptionEditionRow.id)
            .execution_options(synchronize_session=False)
        )
        return await self.get(updated) if updated is not None else None

    async def get_lineage(self, subscription_id: UUID) -> SubscriptionLineage | None:
        row = await self.session.get(
            SubscriptionLineageRow, subscription_id, populate_existing=True
        )
        return lineage_from_row(row) if row is not None else None

    async def save_lineage(
        self, lineage: SubscriptionLineage, *, expected_revision: int | None
    ) -> SubscriptionLineage | None:
        if expected_revision is None:
            if lineage.revision != 1:
                raise ValueError("New lineage begins at revision one.")
            await self._insert_once(SubscriptionLineageRow, lineage_values(lineage))
            stored = await self.get_lineage(lineage.subscription_id)
            return stored if stored == lineage else None
        if lineage.revision != expected_revision + 1:
            raise ValueError("Lineage fences must advance by one.")
        values = lineage_values(lineage)
        values.pop("subscription_id")
        updated = await self.session.scalar(
            update(SubscriptionLineageRow)
            .where(
                SubscriptionLineageRow.subscription_id == lineage.subscription_id,
                SubscriptionLineageRow.revision == expected_revision,
                SubscriptionLineageRow.updated_at <= lineage.updated_at,
            )
            .values(**values)
            .returning(SubscriptionLineageRow.subscription_id)
            .execution_options(synchronize_session=False)
        )
        return await self.get_lineage(updated) if updated is not None else None

    async def add_attempt(self, attempt: EditionAttempt) -> None:
        await self._insert_once(SubscriptionAttemptRow, attempt_values(attempt))
        row = await self.session.get(SubscriptionAttemptRow, attempt.id, populate_existing=True)
        if row is None or attempt_from_row(row) != attempt:
            raise Conflict("A different edition attempt already uses this identity.")

    async def attempts(self, edition_id: UUID, limit: int = 50) -> list[EditionAttempt]:
        _page(limit)
        rows = await self.session.scalars(
            select(SubscriptionAttemptRow)
            .where(SubscriptionAttemptRow.edition_id == edition_id)
            .order_by(SubscriptionAttemptRow.number)
            .limit(limit)
        )
        return [attempt_from_row(row) for row in rows]

    async def add_delivery(self, delivery: EditionDelivery) -> None:
        await self._insert_once(SubscriptionDeliveryRow, delivery_values(delivery))
        row = await self.session.get(SubscriptionDeliveryRow, delivery.id, populate_existing=True)
        if row is None or delivery_from_row(row) != delivery:
            raise Conflict("A different delivery already uses this identity.")

    async def deliveries(self, edition_id: UUID, limit: int = 50) -> list[EditionDelivery]:
        _page(limit)
        rows = await self.session.scalars(
            select(SubscriptionDeliveryRow)
            .where(SubscriptionDeliveryRow.edition_id == edition_id)
            .order_by(SubscriptionDeliveryRow.created_at, SubscriptionDeliveryRow.id)
            .limit(limit)
        )
        return [delivery_from_row(row) for row in rows]

    async def in_app_events(
        self, subscription_id: UUID, *, limit: int = 50, offset: int = 0
    ) -> list[EditionDelivery]:
        _page(limit, offset)
        rows = await self.session.scalars(
            select(SubscriptionDeliveryRow)
            .join(
                SubscriptionEditionRow,
                SubscriptionDeliveryRow.edition_id == SubscriptionEditionRow.id,
            )
            .where(
                SubscriptionEditionRow.subscription_id == subscription_id,
                SubscriptionDeliveryRow.channel == "in_app",
                SubscriptionDeliveryRow.state == "available",
            )
            .order_by(SubscriptionDeliveryRow.created_at.desc(), SubscriptionDeliveryRow.id)
            .limit(limit)
            .offset(offset)
        )
        return [delivery_from_row(row) for row in rows]
