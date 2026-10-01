"""SQL reads for the research-quality scorecard. Visibility and the window apply first.

Only status columns, dimension values, finding rule codes, receipt statuses and token
counts are mapped; titles, report prose and finding messages never leave this module.
"""

from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, String, cast, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from ase.adapters.persistence.access import visibility_predicate
from ase.adapters.persistence.citation_verdict_models import CitationVerdictRow
from ase.adapters.persistence.citation_verdicts import verdict_from_row
from ase.adapters.persistence.models import ReportRow, ReportVersionRow
from ase.adapters.persistence.report_job_models import ReportJobRow
from ase.domain.access import Visibility
from ase.domain.citation_verdicts import CitationVerdict
from ase.domain.research import CollectionStatus, ResearchMode
from ase.domain.research_quality import JobOutcome, VersionOutcome, known
from ase.domain.validation_types import Severity

_DEPTHS = tuple(mode.value for mode in ResearchMode)
_RECEIPTS = tuple(status.value for status in CollectionStatus)
_SEVERITIES = tuple(severity.value for severity in Severity)


def _text(value: Any, limit: int = 120) -> str | None:
    return value if isinstance(value, str) and 0 < len(value) <= limit else None


def _findings(value: Any) -> tuple[tuple[str, str], ...]:
    rows = value if isinstance(value, list) else []
    result = []
    for row in rows:
        if isinstance(row, dict):
            rule, severity = _text(row.get("rule"), 60), known(row.get("severity"), _SEVERITIES)
            if rule and severity:
                result.append((rule, severity))
    return tuple(result)


def _receipts(value: Any) -> tuple[str, ...] | None:
    if not isinstance(value, list):
        return None
    return tuple(
        status
        for row in value
        if isinstance(row, dict) and (status := known(row.get("status"), _RECEIPTS))
    )


def _tokens(value: Any) -> int | None:
    return value if isinstance(value, int) and value >= 0 else None


class SqlResearchQualityReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def versions(
        self, visibility: Visibility, since: datetime, limit: int
    ) -> tuple[int, Sequence[VersionOutcome]]:
        scope = (
            visibility_predicate(ReportRow.created_by, ReportRow.team_id, visibility),
            ReportVersionRow.created_at >= since,
        )
        total = await self._session.scalar(
            select(func.count())
            .select_from(ReportVersionRow)
            .join(ReportRow, ReportRow.id == ReportVersionRow.report_id)
            .where(*scope)
        )
        rows = await self._session.execute(
            select(
                ReportVersionRow.status,
                ReportRow.template,
                ReportRow.scope["research_mode"].as_string(),
                ReportVersionRow.profile_id,
                ReportVersionRow.findings,
                ReportVersionRow.analysis[("research", "attempts")],
                ReportVersionRow.prompt_tokens,
                ReportVersionRow.completion_tokens,
            )
            .join(ReportRow, ReportRow.id == ReportVersionRow.report_id)
            .where(*scope)
            .order_by(ReportVersionRow.created_at.desc(), ReportVersionRow.id)
            .limit(limit)
        )
        return int(total or 0), [
            VersionOutcome(
                status=status,
                template=_text(template, 40),
                depth=known(depth, _DEPTHS),
                connection=str(profile_id) if profile_id else None,
                findings=_findings(findings),
                receipts=_receipts(attempts),
                prompt_tokens=_tokens(prompt),
                completion_tokens=_tokens(completion),
            )
            for status, template, depth, profile_id, findings, attempts, prompt, completion in rows
        ]

    def _payload(self, *path: str) -> ColumnElement[Any]:
        if self._session.get_bind().dialect.name == "sqlite":
            return func.json_extract(ReportJobRow.payload, "$." + ".".join(path), type_=String)
        value: ColumnElement[Any] = cast(ReportJobRow.payload, JSON)[path].as_string()
        return value

    async def jobs(
        self, visibility: Visibility, since: datetime, limit: int
    ) -> tuple[int, Sequence[JobOutcome]]:
        scope = (
            visibility_predicate(ReportJobRow.owner_id, ReportJobRow.team_id, visibility),
            ReportJobRow.created_at >= since,
        )
        total = await self._session.scalar(
            select(func.count()).select_from(ReportJobRow).where(*scope)
        )
        saved = exists().where(ReportVersionRow.id == ReportJobRow.version_id)
        rows = await self._session.execute(
            select(
                ReportJobRow.status,
                ReportJobRow.error,
                self._payload("input", "template_id"),
                self._payload("input", "scope", "research_mode"),
                self._payload("summary", "model"),
                saved,
            )
            .where(*scope)
            .order_by(ReportJobRow.created_at.desc(), ReportJobRow.id)
            .limit(limit)
        )
        return int(total or 0), [
            JobOutcome(
                status=status,
                template=_text(template, 40),
                depth=known(depth, _DEPTHS),
                model=_text(model, 200),
                error=_text(error),
                version_saved=bool(version_saved),
            )
            for status, error, template, depth, model, version_saved in rows
        ]

    async def citation_verdicts(
        self, visibility: Visibility, since: datetime, limit: int
    ) -> tuple[int, Sequence[CitationVerdict]]:
        scope = (
            visibility_predicate(ReportRow.created_by, ReportRow.team_id, visibility),
            CitationVerdictRow.owner_id == ReportRow.created_by,
            CitationVerdictRow.team_id.is_not_distinct_from(ReportRow.team_id),
            CitationVerdictRow.recorded_at >= since,
        )
        joined = select(CitationVerdictRow).join(
            ReportRow, ReportRow.id == CitationVerdictRow.report_id
        )
        total = await self._session.scalar(
            select(func.count()).select_from(joined.where(*scope).subquery())
        )
        rows = await self._session.scalars(
            joined.where(*scope)
            .order_by(CitationVerdictRow.recorded_at.desc(), CitationVerdictRow.id)
            .limit(limit)
        )
        # Reviewer notes are never needed for counts, so they are dropped at the boundary.
        return int(total or 0), [replace(verdict_from_row(row), note=None) for row in rows]
