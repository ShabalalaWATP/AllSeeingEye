"""Visible brief queries; visibility is applied before latest selection and pagination."""

from uuid import UUID

from sqlalchemy import and_, func, select

from ase.adapters.persistence.access import visibility_predicate
from ase.adapters.persistence.research_brief_models import ResearchBriefRevisionRow as Row
from ase.adapters.persistence.research_briefs import SqlResearchBriefRepository, _decode
from ase.application.ports.brief_management import BriefSummary
from ase.domain.access import Visibility
from ase.domain.research_brief import ResearchBrief


class SqlBriefManagementRepository(SqlResearchBriefRepository):
    async def visible(
        self, visibility: Visibility, brief_id: UUID, revision: int | None = None
    ) -> ResearchBrief | None:
        statement = select(Row).where(
            Row.brief_id == brief_id,
            visibility_predicate(Row.owner_id, Row.team_id, visibility),
        )
        if revision is not None:
            statement = statement.where(Row.revision == revision)
        else:
            statement = statement.order_by(Row.revision.desc()).limit(1)
        row = await self.session.scalar(statement.execution_options(populate_existing=True))
        return _decode(row) if row is not None else None

    async def list_visible(
        self, visibility: Visibility, limit: int, offset: int, brief_id: UUID | None = None
    ) -> list[BriefSummary]:
        visible = visibility_predicate(Row.owner_id, Row.team_id, visibility)
        if brief_id is None:
            latest = (
                select(Row.brief_id, func.max(Row.revision).label("revision"))
                .where(visible)
                .group_by(Row.brief_id)
                .subquery()
            )
            statement = (
                select(Row)
                .join(
                    latest,
                    and_(Row.brief_id == latest.c.brief_id, Row.revision == latest.c.revision),
                )
                .order_by(Row.revised_at.desc(), Row.brief_id)
            )
        else:
            statement = (
                select(Row).where(Row.brief_id == brief_id, visible).order_by(Row.revision.desc())
            )
        rows = await self.session.scalars(statement.limit(limit).offset(offset))
        return [
            BriefSummary(
                row.brief_id,
                row.revision,
                row.owner_id,
                row.team_id,
                row.title,
                row.schema_version,
                row.origin,
                row.published,
                row.created_at,
                row.revised_at,
            )
            for row in rows
        ]
