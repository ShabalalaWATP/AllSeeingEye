"""Append-once persistence for exact-version subscription comparisons."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.subscription_comparison_codec import (
    comparison_from_row,
    comparison_values,
)
from ase.adapters.persistence.subscription_edition_models import (
    SubscriptionEditionComparisonRow,
    SubscriptionEditionRow,
)
from ase.domain.errors import Conflict
from ase.domain.subscription_comparisons import EditionComparison


class SqlSubscriptionComparisonRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, comparison: EditionComparison) -> EditionComparison:
        edition = await self.session.get(
            SubscriptionEditionRow, comparison.edition_id, populate_existing=True
        )
        if edition is None or edition.version_id != comparison.current_version_id:
            raise Conflict("Comparison current version does not match its edition.")
        if edition.baseline_version_id != comparison.previous_version_id:
            raise Conflict("Comparison baseline does not match its frozen edition.")
        values = comparison_values(comparison)
        dialect = self.session.get_bind().dialect.name
        if dialect == "sqlite":
            await self.session.execute(
                sqlite_insert(SubscriptionEditionComparisonRow)
                .values(**values)
                .on_conflict_do_nothing()
            )
        elif dialect == "postgresql":
            await self.session.execute(
                pg_insert(SubscriptionEditionComparisonRow)
                .values(**values)
                .on_conflict_do_nothing()
            )
        else:
            raise RuntimeError("Subscription comparisons require SQLite or PostgreSQL.")
        stored = await self.get(comparison.edition_id)
        if stored != comparison:
            raise Conflict("A different immutable edition comparison already exists.")
        return stored

    async def get(self, edition_id: UUID) -> EditionComparison | None:
        row = await self.session.get(
            SubscriptionEditionComparisonRow, edition_id, populate_existing=True
        )
        return comparison_from_row(row) if row is not None else None

    async def list_for(self, edition_ids: list[UUID]) -> dict[UUID, EditionComparison]:
        if len(edition_ids) > 100:
            raise ValueError("Use a bounded subscription history page.")
        if not edition_ids:
            return {}
        rows = await self.session.scalars(
            select(SubscriptionEditionComparisonRow).where(
                SubscriptionEditionComparisonRow.edition_id.in_(edition_ids)
            )
        )
        values = [comparison_from_row(row) for row in rows]
        return {value.edition_id: value for value in values}
