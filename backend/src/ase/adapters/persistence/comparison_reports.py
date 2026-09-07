"""Parameterised title search with visibility applied to both rows and count."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.access import visibility_predicate
from ase.adapters.persistence.models import ReportRow
from ase.adapters.persistence.reports import _record_from_row
from ase.domain.access import Visibility
from ase.domain.report_records import ReportRecord


class SqlComparisonReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def page(
        self, visibility: Visibility, query: str, limit: int, offset: int
    ) -> tuple[list[ReportRecord], int]:
        predicate = visibility_predicate(ReportRow.created_by, ReportRow.team_id, visibility)
        criteria = [predicate]
        if query:
            criteria.append(ReportRow.title.icontains(query, autoescape=True))
        total = await self.session.scalar(
            select(func.count()).select_from(ReportRow).where(*criteria)
        )
        rows = await self.session.scalars(
            select(ReportRow)
            .where(*criteria)
            .order_by(ReportRow.created_at.desc(), ReportRow.id)
            .offset(offset)
            .limit(limit)
            .execution_options(populate_existing=True)
        )
        return [_record_from_row(row) for row in rows], int(total or 0)
