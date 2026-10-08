"""Portable JSON vectors for a bounded, single-process saved report library."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
    and_,
    cast,
    delete,
    exists,
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, validates

from ase.adapters.persistence.access import visibility_predicate
from ase.adapters.persistence.base import Base
from ase.adapters.persistence.models import ReportRow
from ase.domain.access import Visibility
from ase.domain.report_search import IndexedReport, checked_vector


class ReportEmbeddingRow(Base):
    __tablename__ = "report_embeddings"

    report_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("reports.id", ondelete="CASCADE"), primary_key=True
    )
    version: Mapped[int] = mapped_column(Integer)
    fingerprint: Mapped[str] = mapped_column(String(64))
    vector: Mapped[list[float]] = mapped_column(JSON)
    vector_valid: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")

    @validates("vector")
    def _validity(self, _key: str, value: list[float]) -> list[float]:
        try:
            checked_vector(value)
        except (ValueError, OverflowError):
            self.vector_valid = False
        else:
            self.vector_valid = True
        return value


def _decoded(rows: Sequence[tuple[UUID, int, str, str | None]]) -> list[IndexedReport]:
    entries = []
    for report_id, version, fingerprint, text in rows:
        try:
            vector = checked_vector(json.loads(text) if text is not None else None)
        except (ValueError, OverflowError, RecursionError):
            continue
        entries.append(IndexedReport(report_id, version, fingerprint, vector))
    return entries


class SqlReportEmbeddingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def status_counts(
        self, visibility: Visibility, fingerprint: str | None, limit: int
    ) -> tuple[int, int]:
        visible = (
            select(ReportRow.id, ReportRow.latest_version)
            .where(visibility_predicate(ReportRow.created_by, ReportRow.team_id, visibility))
            .order_by(ReportRow.created_at.desc(), ReportRow.id)
            .limit(limit)
            .subquery()
        )
        row = (
            await self._session.execute(
                select(func.count(ReportEmbeddingRow.report_id), func.count(visible.c.id))
                .select_from(visible)
                .outerjoin(
                    ReportEmbeddingRow,
                    and_(
                        ReportEmbeddingRow.report_id == visible.c.id,
                        ReportEmbeddingRow.version == visible.c.latest_version,
                        ReportEmbeddingRow.fingerprint == fingerprint,
                        ReportEmbeddingRow.vector_valid.is_(True),
                    ),
                )
            )
        ).one()
        return int(row[0]), int(row[1])

    async def has_current(self, report_ids: Sequence[UUID], fingerprint: str) -> bool:
        if not report_ids:
            return False
        found = await self._session.scalar(
            select(
                exists().where(
                    ReportEmbeddingRow.report_id == ReportRow.id,
                    ReportEmbeddingRow.report_id.in_(report_ids),
                    ReportEmbeddingRow.version == ReportRow.latest_version,
                    ReportEmbeddingRow.fingerprint == fingerprint,
                    ReportEmbeddingRow.vector_valid.is_(True),
                )
            )
        )
        return bool(found)

    async def current(self, report_ids: Sequence[UUID], fingerprint: str) -> list[IndexedReport]:
        if not report_ids:
            return []
        # Raw JSON text: decoding up to 1,000 x 4,096 numbers happens off the event loop.
        rows = await self._session.execute(
            select(
                ReportEmbeddingRow.report_id,
                ReportEmbeddingRow.version,
                ReportEmbeddingRow.fingerprint,
                cast(ReportEmbeddingRow.vector, Text),
            )
            .join(ReportRow, ReportRow.id == ReportEmbeddingRow.report_id)
            .where(
                ReportEmbeddingRow.report_id.in_(report_ids),
                ReportEmbeddingRow.version == ReportRow.latest_version,
                ReportEmbeddingRow.fingerprint == fingerprint,
            )
        )
        raw = [(row[0], row[1], row[2], row[3]) for row in rows]
        return await asyncio.to_thread(_decoded, raw)

    async def save(self, entry: IndexedReport) -> bool:
        current = await self._session.scalar(
            select(ReportRow.id)
            .where(ReportRow.id == entry.report_id, ReportRow.latest_version == entry.version)
            .with_for_update()
        )
        if current is None:
            return False
        row = await self._session.get(ReportEmbeddingRow, entry.report_id)
        if row is None:
            row = ReportEmbeddingRow(report_id=entry.report_id)
            self._session.add(row)
        row.version = entry.version
        row.fingerprint = entry.fingerprint
        row.vector = list(checked_vector(entry.vector))
        await self._session.flush()
        return True

    async def prune_obsolete(self) -> None:
        valid = select(ReportRow.id).where(ReportRow.latest_version == ReportEmbeddingRow.version)
        await self._session.execute(
            delete(ReportEmbeddingRow).where(ReportEmbeddingRow.report_id.not_in(valid))
        )

    async def capacity_for(self, report_ids: Sequence[UUID], limit: int) -> frozenset[UUID]:
        stored = set(await self._session.scalars(select(ReportEmbeddingRow.report_id)))
        slots = max(0, limit - len(stored))
        selected: set[UUID] = set()
        for report_id in report_ids:
            if report_id in stored:
                selected.add(report_id)
            elif slots:
                selected.add(report_id)
                slots -= 1
        return frozenset(selected)
