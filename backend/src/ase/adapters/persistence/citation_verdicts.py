"""SQL repository for append-only citation verdicts on exact saved report versions."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.citation_verdict_models import CitationVerdictRow
from ase.domain.citation_verdicts import (
    CitationAnchor,
    CitationVerdict,
    CitationVerdictValue,
)


def verdict_from_row(row: CitationVerdictRow) -> CitationVerdict:
    return CitationVerdict(
        row.id,
        row.report_id,
        row.report_version_id,
        row.version_number,
        CitationAnchor(
            row.judgement_id,
            row.label,
            "supporting" if row.relation == "supporting" else "contradicting",
        ),
        CitationVerdictValue(row.verdict),
        row.note,
        row.owner_id,
        row.team_id,
        row.reviewer_id,
        row.recorded_at,
    )


class SqlCitationVerdictRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def for_version(self, report_version_id: UUID, limit: int) -> tuple[CitationVerdict, ...]:
        rows = await self._session.scalars(
            select(CitationVerdictRow)
            .where(CitationVerdictRow.report_version_id == report_version_id)
            .order_by(CitationVerdictRow.recorded_at, CitationVerdictRow.id)
            .limit(limit)
        )
        return tuple(verdict_from_row(row) for row in rows)

    async def count_for_version(self, report_version_id: UUID) -> int:
        total = await self._session.scalar(
            select(func.count())
            .select_from(CitationVerdictRow)
            .where(CitationVerdictRow.report_version_id == report_version_id)
        )
        return int(total or 0)

    async def count_for_anchor(self, report_version_id: UUID, anchor: CitationAnchor) -> int:
        total = await self._session.scalar(
            select(func.count())
            .select_from(CitationVerdictRow)
            .where(
                CitationVerdictRow.report_version_id == report_version_id,
                CitationVerdictRow.judgement_id == anchor.judgement_id,
                CitationVerdictRow.label == anchor.label,
                CitationVerdictRow.relation == anchor.relation,
            )
        )
        return int(total or 0)

    async def add(self, verdict: CitationVerdict) -> None:
        self._session.add(
            CitationVerdictRow(
                id=verdict.id,
                report_id=verdict.report_id,
                report_version_id=verdict.report_version_id,
                version_number=verdict.version_number,
                judgement_id=verdict.anchor.judgement_id,
                label=verdict.anchor.label,
                relation=verdict.anchor.relation,
                verdict=verdict.verdict.value,
                note=verdict.note,
                owner_id=verdict.owner_id,
                team_id=verdict.team_id,
                reviewer_id=verdict.reviewer_id,
                recorded_at=verdict.recorded_at,
            )
        )
        await self._session.flush()
