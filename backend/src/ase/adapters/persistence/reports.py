"""Report repository: records, versions and their frozen evidence as JSON."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.models import ReportRow, ReportVersionRow
from ase.domain.report_records import (
    ReportRecord,
    ReportVersion,
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
    )


def _version_from_row(row: ReportVersionRow) -> ReportVersion:
    return ReportVersion(
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
            )
        )
        self._session.add(
            ReportVersionRow(
                id=version.id,
                report_id=version.report_id,
                number=version.number,
                status=version.status.value,
                body=body_to_dict(version.body),
                findings=findings_to_list(version.findings),
                evidence=evidence_to_list(version.evidence),
                quality=quality_to_dict(version.quality),
                markdown=version.markdown,
                profile_id=version.profile_id,
                model=version.model,
                prompt_tokens=version.prompt_tokens,
                completion_tokens=version.completion_tokens,
                latency_ms=version.latency_ms,
                attempts=version.attempts,
                created_at=version.created_at,
            )
        )
        await self._session.flush()

    async def get(self, report_id: UUID) -> ReportRecord | None:
        row = await self._session.get(ReportRow, report_id)
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

    async def list_recent(self, limit: int) -> list[ReportRecord]:
        rows = await self._session.scalars(
            select(ReportRow).order_by(ReportRow.created_at.desc()).limit(limit)
        )
        return [_record_from_row(row) for row in rows]

    async def delete(self, report_id: UUID) -> None:
        await self._session.execute(
            delete(ReportVersionRow).where(ReportVersionRow.report_id == report_id)
        )
        await self._session.execute(delete(ReportRow).where(ReportRow.id == report_id))
        await self._session.flush()
