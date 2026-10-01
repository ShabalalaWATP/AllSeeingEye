"""Team copy provenance and counts of the personal records a copy leaves behind."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.claim_models import ClaimRow
from ase.adapters.persistence.map_view_models import MapViewRevisionRow
from ase.adapters.persistence.original_asset_models import OriginalAssetRow
from ase.adapters.persistence.original_passage_models import OriginalPassageRow
from ase.adapters.persistence.report_team_copy_models import ReportTeamCopyRow
from ase.adapters.persistence.source_review_models import SourceReviewSnapshotRow
from ase.domain.errors import Conflict
from ase.domain.report_team_copy import LinkedArtefacts, ReportTeamCopy, TeamCopyOmission


def _domain(row: ReportTeamCopyRow) -> ReportTeamCopy:
    return ReportTeamCopy(
        id=row.id,
        report_id=row.report_id,
        team_id=row.team_id,
        source_report_id=row.source_report_id,
        source_version_id=row.source_version_id,
        source_version_number=row.source_version_number,
        copied_by=row.copied_by,
        copied_at=row.copied_at,
        content_sha256=row.content_sha256,
        disclosed_labels=tuple(str(label) for label in row.disclosed_labels),
        omissions=tuple(TeamCopyOmission(str(value)) for value in row.omissions),
    )


async def delete_team_copy_provenance(session: AsyncSession, report_id: UUID) -> None:
    """Explicit cleanup for SQLite connections without foreign key enforcement."""
    await session.execute(delete(ReportTeamCopyRow).where(ReportTeamCopyRow.report_id == report_id))


class SqlReportTeamCopyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find(self, source_version_id: UUID, team_id: UUID) -> ReportTeamCopy | None:
        row = (
            await self._session.scalars(
                select(ReportTeamCopyRow)
                .where(
                    ReportTeamCopyRow.source_version_id == source_version_id,
                    ReportTeamCopyRow.team_id == team_id,
                )
                .execution_options(populate_existing=True)
            )
        ).first()
        return _domain(row) if row is not None else None

    async def for_report(self, report_id: UUID) -> ReportTeamCopy | None:
        row = (
            await self._session.scalars(
                select(ReportTeamCopyRow).where(ReportTeamCopyRow.report_id == report_id)
            )
        ).first()
        return _domain(row) if row is not None else None

    async def add(self, copy: ReportTeamCopy) -> None:
        self._session.add(
            ReportTeamCopyRow(
                id=copy.id,
                report_id=copy.report_id,
                team_id=copy.team_id,
                source_report_id=copy.source_report_id,
                source_version_id=copy.source_version_id,
                source_version_number=copy.source_version_number,
                copied_by=copy.copied_by,
                copied_at=copy.copied_at,
                content_sha256=copy.content_sha256,
                disclosed_labels=list(copy.disclosed_labels),
                omissions=[value.value for value in copy.omissions],
            )
        )
        try:
            await self._session.flush()
        except IntegrityError:
            raise Conflict("This version has already been copied to the team.") from None

    async def linked_artefacts(self, version_id: UUID) -> LinkedArtefacts:
        async def count(statement: Any) -> int:
            return int(await self._session.scalar(statement) or 0)

        return LinkedArtefacts(
            claims=await count(
                select(func.count()).where(ClaimRow.report_version_id == version_id)
            ),
            original_files=await count(
                select(func.count()).where(OriginalAssetRow.report_version_id == version_id)
            ),
            original_passages=await count(
                select(func.count()).where(OriginalPassageRow.report_version_id == version_id)
            ),
            reviewed_snapshots=await count(
                select(func.count()).where(SourceReviewSnapshotRow.report_version_id == version_id)
            ),
            map_views=await count(
                select(func.count(func.distinct(MapViewRevisionRow.view_id))).where(
                    MapViewRevisionRow.report_version_id == version_id
                )
            ),
        )
