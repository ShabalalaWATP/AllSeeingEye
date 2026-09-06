"""Parent-authorised SQL pagination for the current user's library only."""

from uuid import UUID

from sqlalchemy import delete, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.access import visibility_predicate
from ase.adapters.persistence.library_models import ResearchLibraryRow, ResearchLibraryTagRow
from ase.adapters.persistence.models import ReportRow
from ase.adapters.persistence.reports import _record_from_row
from ase.domain.access import Visibility
from ase.domain.research_library import LibraryItem, LibraryPage, LibraryPreference


class SqlResearchLibraryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, user_id: UUID, report_id: UUID) -> LibraryPreference:
        row = await self.session.get(
            ResearchLibraryRow, (user_id, report_id), populate_existing=True
        )
        if row is None:
            return LibraryPreference()
        tags = tuple(
            (
                await self.session.scalars(
                    select(ResearchLibraryTagRow.tag)
                    .where(
                        ResearchLibraryTagRow.user_id == user_id,
                        ResearchLibraryTagRow.report_id == report_id,
                    )
                    .order_by(ResearchLibraryTagRow.tag)
                )
            ).all()
        )
        return LibraryPreference(row.favourite, tags, row.note, row.updated_at)

    async def save(self, user_id: UUID, report_id: UUID, value: LibraryPreference) -> None:
        row = await self.session.get(ResearchLibraryRow, (user_id, report_id))
        if row is None:
            row = ResearchLibraryRow(user_id=user_id, report_id=report_id)
            self.session.add(row)
        row.favourite, row.note = value.favourite, value.note
        if value.updated_at is None:
            raise ValueError("A saved library preference requires an update time")
        row.updated_at = value.updated_at
        await self.session.flush()
        await self.session.execute(
            delete(ResearchLibraryTagRow).where(
                ResearchLibraryTagRow.user_id == user_id,
                ResearchLibraryTagRow.report_id == report_id,
            )
        )
        self.session.add_all(
            [
                ResearchLibraryTagRow(user_id=user_id, report_id=report_id, tag=tag)
                for tag in value.tags
            ]
        )
        await self.session.flush()

    async def remove(self, user_id: UUID, report_id: UUID) -> None:
        await self.session.execute(
            delete(ResearchLibraryRow).where(
                ResearchLibraryRow.user_id == user_id,
                ResearchLibraryRow.report_id == report_id,
            )
        )

    async def list_visible(
        self,
        visibility: Visibility,
        limit: int,
        offset: int,
        favourite_only: bool,
        tag: str | None,
    ) -> LibraryPage:
        filters = [
            ResearchLibraryRow.user_id == visibility.user_id,
            visibility_predicate(ReportRow.created_by, ReportRow.team_id, visibility),
        ]
        if favourite_only:
            filters.append(ResearchLibraryRow.favourite.is_(True))
        if tag is not None:
            filters.append(
                exists().where(
                    ResearchLibraryTagRow.user_id == ResearchLibraryRow.user_id,
                    ResearchLibraryTagRow.report_id == ResearchLibraryRow.report_id,
                    ResearchLibraryTagRow.tag == tag,
                )
            )
        scope = (
            select(ResearchLibraryRow, ReportRow)
            .join(
                ReportRow,
                ReportRow.id == ResearchLibraryRow.report_id,
            )
            .where(*filters)
        )
        total = int(
            await self.session.scalar(select(func.count()).select_from(scope.subquery())) or 0
        )
        rows = (
            await self.session.execute(
                scope.order_by(
                    ResearchLibraryRow.updated_at.desc(),
                    ResearchLibraryRow.report_id,
                )
                .offset(offset)
                .limit(limit)
            )
        ).all()
        ids = [row.report_id for row, _ in rows]
        tags: dict[UUID, list[str]] = {}
        if ids:
            for row in (
                await self.session.scalars(
                    select(ResearchLibraryTagRow)
                    .where(
                        ResearchLibraryTagRow.user_id == visibility.user_id,
                        ResearchLibraryTagRow.report_id.in_(ids),
                    )
                    .order_by(ResearchLibraryTagRow.tag)
                )
            ).all():
                tags.setdefault(row.report_id, []).append(row.tag)
        return LibraryPage(
            tuple(
                LibraryItem(
                    _record_from_row(report),
                    LibraryPreference(
                        row.favourite, tuple(tags.get(row.report_id, ())), row.note, row.updated_at
                    ),
                )
                for row, report in rows
            ),
            total,
            offset,
            limit,
        )
