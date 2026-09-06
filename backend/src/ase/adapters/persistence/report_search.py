"""Portable JSON vectors for a bounded, single-process saved report library."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import JSON, ForeignKey, Integer, String, Uuid, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base
from ase.adapters.persistence.models import ReportRow
from ase.domain.report_search import IndexedReport, checked_vector


class ReportEmbeddingRow(Base):
    __tablename__ = "report_embeddings"

    report_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("reports.id", ondelete="CASCADE"), primary_key=True
    )
    version: Mapped[int] = mapped_column(Integer)
    fingerprint: Mapped[str] = mapped_column(String(64))
    vector: Mapped[list[float]] = mapped_column(JSON)


class SqlReportEmbeddingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def current(self, report_ids: Sequence[UUID], fingerprint: str) -> list[IndexedReport]:
        rows = await self._session.scalars(
            select(ReportEmbeddingRow)
            .join(ReportRow, ReportRow.id == ReportEmbeddingRow.report_id)
            .where(
                ReportEmbeddingRow.report_id.in_(report_ids),
                ReportEmbeddingRow.version == ReportRow.latest_version,
                ReportEmbeddingRow.fingerprint == fingerprint,
            )
        )
        entries = []
        for row in rows:
            try:
                vector = checked_vector(row.vector)
            except (ValueError, OverflowError):
                continue
            entries.append(IndexedReport(row.report_id, row.version, row.fingerprint, vector))
        return entries

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
