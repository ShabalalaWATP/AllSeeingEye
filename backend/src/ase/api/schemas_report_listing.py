"""Saved report summaries and pagination metadata."""

from datetime import datetime
from typing import Any, Self
from uuid import UUID

from pydantic import BaseModel

from ase.domain.report_listing import effective_origin
from ase.domain.report_records import ReportRecord
from ase.domain.reports import ReportOrigin, ReportStatus


class ReportSummaryOut(BaseModel):
    id: UUID
    template: str
    title: str
    scope: dict[str, Any]
    period_from: datetime
    period_to: datetime
    status: ReportStatus
    created_by: UUID
    created_at: datetime
    latest_version: int
    team_id: UUID | None
    origin: ReportOrigin

    @classmethod
    def from_record(cls, record: ReportRecord) -> Self:
        return cls(
            id=record.id,
            template=record.template,
            title=record.title,
            scope=dict(record.scope),
            period_from=record.period_from,
            period_to=record.period_to,
            status=record.status,
            created_by=record.created_by,
            created_at=record.created_at,
            latest_version=record.latest_version,
            team_id=record.team_id,
            origin=effective_origin(record.scope),
        )


class ReportsOut(BaseModel):
    items: list[ReportSummaryOut]
    limit: int
    offset: int
    has_more: bool
