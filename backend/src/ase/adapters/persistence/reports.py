"""Report repository: records, versions and their frozen evidence as JSON."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.access import visibility_predicate
from ase.adapters.persistence.models import ReportRow, ReportVersionRow
from ase.adapters.persistence.report_search import ReportEmbeddingRow
from ase.domain.access import Visibility
from ase.domain.errors import NotFound
from ase.domain.report_records import (
    ReportRecord,
    ReportVersion,
    analysis_from_dict,
    analysis_to_dict,
    body_from_dict,
    body_to_dict,
    evidence_from_list,
    evidence_to_list,
    findings_from_list,
    findings_to_list,
    quality_from_dict,
    quality_to_dict,
)
from ase.domain.reports import ReportStatus


def _record_from_row(row: ReportRow) -> ReportRecord:
    return ReportRecord(
        id=row.id,
        template=row.template,
        title=row.title,
        scope=dict(row.scope),
        period_from=row.period_from,
        period_to=row.period_to,
        data_cutoff=row.data_cutoff,
        status=ReportStatus(row.status),
        created_by=row.created_by,
        created_at=row.created_at,
        latest_version=row.latest_version,
        team_id=row.team_id,
    )


def _version_from_row(row: ReportVersionRow) -> ReportVersion:
    direction, advocacy = analysis_from_dict(row.analysis)
    period = (row.analysis or {}).get("period") or {}
    return ReportVersion(
        direction=direction,
        advocacy=advocacy,
        id=row.id,
        report_id=row.report_id,
        number=row.number,
        status=ReportStatus(row.status),
        body=body_from_dict(row.body),
        findings=findings_from_list(list(row.findings)),
        evidence=evidence_from_list(list(row.evidence)),
        quality=quality_from_dict(row.quality),
        markdown=row.markdown,
        profile_id=row.profile_id,
        model=row.model,
        prompt_tokens=row.prompt_tokens,
        completion_tokens=row.completion_tokens,
        latency_ms=row.latency_ms,
        attempts=row.attempts,
        created_at=row.created_at,
        period_from=datetime.fromisoformat(period["from"]) if period.get("from") else None,
        period_to=datetime.fromisoformat(period["to"]) if period.get("to") else None,
        data_cutoff=datetime.fromisoformat(period["cutoff"]) if period.get("cutoff") else None,
    )


def _version_row(version: ReportVersion) -> ReportVersionRow:
    return ReportVersionRow(
        id=version.id,
        report_id=version.report_id,
        number=version.number,
        status=version.status.value,
        body=body_to_dict(version.body),
        findings=findings_to_list(version.findings),
        evidence=evidence_to_list(version.evidence),
        quality=quality_to_dict(version.quality),
        analysis=analysis_to_dict(version),
        markdown=version.markdown,
        profile_id=version.profile_id,
        model=version.model,
        prompt_tokens=version.prompt_tokens,
        completion_tokens=version.completion_tokens,
        latency_ms=version.latency_ms,
        attempts=version.attempts,
        created_at=version.created_at,
    )


class SqlReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: ReportRecord, version: ReportVersion) -> None:
        self._session.add(
            ReportRow(
                id=record.id,
                template=record.template,
                title=record.title,
                scope=dict(record.scope),
                period_from=record.period_from,
                period_to=record.period_to,
                data_cutoff=record.data_cutoff,
                status=record.status.value,
                created_by=record.created_by,
                created_at=record.created_at,
                latest_version=record.latest_version,
                team_id=record.team_id,
            )
        )
        self._session.add(_version_row(version))
        await self._session.flush()

    async def add_version(self, record: ReportRecord, version: ReportVersion) -> None:
        row = await self._session.get(ReportRow, record.id)
        if row is None:
            raise NotFound()
        row.status = record.status.value
        row.latest_version = record.latest_version
        row.period_from = record.period_from
        row.period_to = record.period_to
        row.data_cutoff = record.data_cutoff
        self._session.add(_version_row(version))
        await self._session.flush()

    async def get(self, report_id: UUID) -> ReportRecord | None:
        row = await self._session.get(ReportRow, report_id, populate_existing=True)
        return _record_from_row(row) if row else None

    async def get_version(self, report_id: UUID, number: int) -> ReportVersion | None:
        row = (
            await self._session.scalars(
                select(ReportVersionRow).where(
                    ReportVersionRow.report_id == report_id, ReportVersionRow.number == number
                )
            )
        ).first()
        return _version_from_row(row) if row else None

    async def set_archives(
        self, version_id: UUID, archives: Mapping[str, str], markdown: str
    ) -> None:
        row = await self._session.get(ReportVersionRow, version_id)
        if row is None:
            return
        # A new list, so the JSON column registers the change.
        row.evidence = [
            {**item, "archive_url": archives.get(str(item.get("label")), item.get("archive_url"))}
            for item in row.evidence
        ]
        row.markdown = markdown
        await self._session.flush()

    async def list_recent(self, limit: int) -> list[ReportRecord]:
        rows = await self._session.scalars(
            select(ReportRow).order_by(ReportRow.created_at.desc()).limit(limit)
        )
        return [_record_from_row(row) for row in rows]

    async def list_visible(self, visibility: Visibility, limit: int) -> list[ReportRecord]:
        rows = await self._session.scalars(
            select(ReportRow)
            .where(visibility_predicate(ReportRow.created_by, ReportRow.team_id, visibility))
            .order_by(ReportRow.created_at.desc(), ReportRow.id)
            .limit(limit)
            .execution_options(populate_existing=True)
        )
        return [_record_from_row(row) for row in rows]

    async def delete(self, report_id: UUID) -> None:
        await self._session.execute(
            delete(ReportEmbeddingRow).where(ReportEmbeddingRow.report_id == report_id)
        )
        await self._session.execute(
            delete(ReportVersionRow).where(ReportVersionRow.report_id == report_id)
        )
        await self._session.execute(delete(ReportRow).where(ReportRow.id == report_id))
        await self._session.flush()
