"""SQL reads for a source track record: visibility, then the report bound, then citations.

The population's text prefilter only narrows rows; every candidate is decoded and matched
exactly on its frozen `source_id`. Identifiers reaching it are plain ASCII that JSON never
escapes.
Review and verdict scans filter to the relevant reports and versions in SQL before their
row limits apply, so unrelated rows cannot crowd relevant ones out of the bound.
"""

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, ColumnElement, String, Text, and_, cast, func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.access import visibility_predicate
from ase.adapters.persistence.citation_verdict_models import CitationVerdictRow
from ase.adapters.persistence.citation_verdicts import verdict_from_row
from ase.adapters.persistence.models import ReportRow, ReportVersionRow
from ase.adapters.persistence.source_review_models import (
    SourceReviewHeadRow,
    SourceReviewRevisionRow,
)
from ase.domain.access import Visibility
from ase.domain.citation_verdicts import CitationVerdict
from ase.domain.report_records import body_from_dict, evidence_from_list
from ase.domain.reports import ReportStatus
from ase.domain.source_review_records import decode_source_review
from ase.domain.source_reviews import SourceReviewRevision
from ase.domain.source_track_record import CitedVersion, TrackRecordPopulation


class SqlSourceTrackRecordReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def population(
        self, visibility: Visibility, source_id: str, limit: int
    ) -> TrackRecordPopulation:
        visible = visibility_predicate(ReportRow.created_by, ReportRow.team_id, visibility)
        latest = (
            select(ReportRow.id, ReportRow.title, ReportRow.latest_version)
            .where(visible)
            .order_by(ReportRow.created_at.desc(), ReportRow.id)
            .limit(limit)
            .subquery()
        )
        total = await self._session.scalar(
            select(func.count()).select_from(ReportRow).where(visible)
        )
        report_ids: frozenset[UUID] = frozenset(await self._session.scalars(select(latest.c.id)))
        rows = await self._session.execute(
            select(
                latest.c.id,
                latest.c.title,
                ReportVersionRow.number,
                ReportVersionRow.status,
                ReportVersionRow.created_at,
                ReportVersionRow.body,
                ReportVersionRow.evidence,
            )
            .join(
                ReportVersionRow,
                and_(
                    ReportVersionRow.report_id == latest.c.id,
                    ReportVersionRow.number == latest.c.latest_version,
                ),
            )
            .where(cast(ReportVersionRow.evidence, Text).contains(source_id, autoescape=True))
        )
        versions = []
        for report_id, title, number, status, saved_at, body, evidence in rows:
            mine: list[Mapping[str, Any]] = [
                row
                for row in evidence or ()
                if isinstance(row, dict) and row.get("source_id") == source_id
            ]
            if mine:
                versions.append(
                    CitedVersion(
                        report_id,
                        title,
                        number,
                        ReportStatus(status),
                        saved_at,
                        body_from_dict(body),
                        evidence_from_list(mine),
                    )
                )
        return TrackRecordPopulation(limit, int(total or 0), report_ids, tuple(versions))

    async def reviews(
        self, visibility: Visibility, source_id: str, report_ids: frozenset[UUID], limit: int
    ) -> tuple[SourceReviewRevision, ...]:
        if not report_ids:
            return ()
        rows = await self._session.execute(
            select(
                SourceReviewRevisionRow, SourceReviewHeadRow.owner_id, SourceReviewHeadRow.team_id
            )
            .join(
                SourceReviewHeadRow,
                and_(
                    SourceReviewHeadRow.key == SourceReviewRevisionRow.head_key,
                    SourceReviewHeadRow.latest_id == SourceReviewRevisionRow.id,
                ),
            )
            .where(
                visibility_predicate(
                    SourceReviewHeadRow.owner_id, SourceReviewHeadRow.team_id, visibility
                ),
                self._review_target("source_id") == source_id,
                self._review_target("report_id").in_(sorted(str(item) for item in report_ids)),
            )
            .order_by(SourceReviewRevisionRow.created_at.desc(), SourceReviewRevisionRow.id)
            .limit(limit)
        )
        result = []
        for row, owner_id, team_id in rows:
            value = decode_source_review(row.payload, row.payload_sha256, row.payload_bytes)
            if (value.scope.owner_id, value.scope.team_id) != (owner_id, team_id) or (
                value.review.id != str(row.id)
            ):
                raise ValueError("Source review indexes do not match saved content.")
            if value.target.source_id == source_id and value.target.report_id in report_ids:
                result.append(value)
        return tuple(result)

    async def verdicts(
        self, visibility: Visibility, versions: frozenset[tuple[UUID, int]], limit: int
    ) -> tuple[CitationVerdict, ...]:
        if not versions:
            return ()
        rows = await self._session.scalars(
            select(CitationVerdictRow)
            .join(ReportRow, ReportRow.id == CitationVerdictRow.report_id)
            .where(
                visibility_predicate(ReportRow.created_by, ReportRow.team_id, visibility),
                CitationVerdictRow.owner_id == ReportRow.created_by,
                CitationVerdictRow.team_id.is_not_distinct_from(ReportRow.team_id),
                CitationVerdictRow.report_id.in_({report_id for report_id, _ in versions}),
                tuple_(CitationVerdictRow.report_id, CitationVerdictRow.version_number).in_(
                    sorted(versions)
                ),
            )
            .order_by(CitationVerdictRow.recorded_at.desc(), CitationVerdictRow.id)
            .limit(limit)
        )
        return tuple(
            verdict_from_row(row) for row in rows if (row.report_id, row.version_number) in versions
        )

    def _review_target(self, field: str) -> ColumnElement[Any]:
        """One frozen target field of a review revision's JSON text payload."""

        payload = SourceReviewRevisionRow.payload
        if self._session.get_bind().dialect.name == "sqlite":
            return func.json_extract(payload, f"$.target.{field}", type_=String)
        value: ColumnElement[Any] = cast(payload, JSON)[("target", field)].as_string()
        return value
