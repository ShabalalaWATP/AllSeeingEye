"""Immutable revision writes and parent-authorised SQL pagination for saved maps."""

from uuid import UUID

from sqlalchemy import and_, delete, exists, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.access import visibility_predicate
from ase.adapters.persistence.map_view_models import MapViewRevisionRow, MapViewRow
from ase.adapters.persistence.models import ReportRow, ReportVersionRow
from ase.domain.access import Visibility
from ase.domain.map_view_records import revision_bytes, state_from_dict, state_to_dict
from ase.domain.map_views import MapView, MapViewPage, MapViewRevision, MapViewSummary


def _view(row: MapViewRow) -> MapView:
    return MapView(
        row.id,
        row.report_id,
        row.created_by,
        row.team_id,
        row.latest_revision_id,
        row.created_at,
        row.archived,
    )


def _revision(row: MapViewRevisionRow) -> MapViewRevision:
    return MapViewRevision(
        row.id,
        row.view_id,
        row.number,
        row.title,
        row.report_version_id,
        row.report_version_number,
        state_from_dict(row.state),
        row.evidence_sha256,
        row.content_sha256,
        row.created_by,
        row.created_at,
    )


def _revision_row(value: MapViewRevision) -> MapViewRevisionRow:
    return MapViewRevisionRow(
        id=value.id,
        view_id=value.view_id,
        number=value.number,
        title=value.title,
        report_version_id=value.report_version_id,
        report_version_number=value.report_version_number,
        state=state_to_dict(value.state),
        evidence_sha256=value.evidence_sha256,
        content_sha256=value.content_sha256,
        byte_size=revision_bytes(value.state, value.title),
        created_by=value.created_by,
        created_at=value.created_at,
    )


class SqlMapViewRepository:
    """The application holds its shared write guard for quotas and authorisation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, view_id: UUID) -> MapView | None:
        row = await self.session.get(MapViewRow, view_id, populate_existing=True)
        return _view(row) if row else None

    async def revision(self, view_id: UUID, revision_id: UUID) -> MapViewRevision | None:
        row = await self.session.scalar(
            select(MapViewRevisionRow)
            .where(
                MapViewRevisionRow.view_id == view_id,
                MapViewRevisionRow.id == revision_id,
            )
            .execution_options(populate_existing=True)
        )
        return _revision(row) if row else None

    async def list_visible(
        self,
        visibility: Visibility,
        report_id: UUID,
        limit: int,
        offset: int,
    ) -> MapViewPage:
        scope = (
            select(
                MapViewRow,
                MapViewRevisionRow.title,
                MapViewRevisionRow.number,
                MapViewRevisionRow.report_version_number,
                MapViewRevisionRow.created_at,
            )
            .join(ReportRow, ReportRow.id == MapViewRow.report_id)
            .join(
                MapViewRevisionRow,
                and_(
                    MapViewRevisionRow.id == MapViewRow.latest_revision_id,
                    MapViewRevisionRow.view_id == MapViewRow.id,
                ),
            )
            .where(
                MapViewRow.report_id == report_id,
                MapViewRow.archived.is_(False),
                visibility_predicate(MapViewRow.created_by, MapViewRow.team_id, visibility),
                visibility_predicate(ReportRow.created_by, ReportRow.team_id, visibility),
            )
        )
        total = int(
            await self.session.scalar(select(func.count()).select_from(scope.subquery())) or 0
        )
        rows = (
            await self.session.execute(
                scope.order_by(MapViewRevisionRow.created_at.desc(), MapViewRow.id)
                .offset(offset)
                .limit(limit)
                .execution_options(populate_existing=True)
            )
        ).all()
        return MapViewPage(
            tuple(
                MapViewSummary(_view(view), title, number, report_version_number, created_at)
                for view, title, number, report_version_number, created_at in rows
            ),
            total,
            offset,
            limit,
        )

    async def scope_usage(self, owner_id: UUID, team_id: UUID | None) -> tuple[int, int]:
        scope = (
            MapViewRow.team_id == team_id
            if team_id is not None
            else and_(
                MapViewRow.team_id.is_(None),
                MapViewRow.created_by == owner_id,
            )
        )
        count = int(
            await self.session.scalar(select(func.count()).select_from(MapViewRow).where(scope))
            or 0
        )
        size = int(
            await self.session.scalar(
                select(func.sum(MapViewRevisionRow.byte_size))
                .join(
                    MapViewRow,
                    MapViewRow.id == MapViewRevisionRow.view_id,
                )
                .where(scope)
            )
            or 0
        )
        return count, size

    async def create(self, view: MapView, revision: MapViewRevision) -> None:
        if (
            revision.view_id != view.id
            or revision.id != view.latest_revision_id
            or revision.number != 1
        ):
            raise ValueError("Initial map revision does not match its view")
        anchor = await self.session.scalar(
            select(ReportVersionRow.id).where(
                ReportVersionRow.id == revision.report_version_id,
                ReportVersionRow.report_id == view.report_id,
                ReportVersionRow.number == revision.report_version_number,
            )
        )
        if anchor is None:
            raise ValueError("Map revision requires its exact parent report version")
        row = _revision_row(revision)
        self.session.add(
            MapViewRow(
                id=view.id,
                report_id=view.report_id,
                created_by=view.created_by,
                team_id=view.team_id,
                latest_revision_id=view.latest_revision_id,
                created_at=view.created_at,
                archived=view.archived,
            )
        )
        await self.session.flush()
        self.session.add(row)
        await self.session.flush()

    async def append(self, revision: MapViewRevision, base_revision_id: UUID) -> bool:
        row = _revision_row(revision)
        previous = exists().where(
            MapViewRevisionRow.id == base_revision_id,
            MapViewRevisionRow.view_id == MapViewRow.id,
            MapViewRevisionRow.number == revision.number - 1,
        )
        anchor = exists().where(
            ReportVersionRow.id == revision.report_version_id,
            ReportVersionRow.report_id == MapViewRow.report_id,
            ReportVersionRow.number == revision.report_version_number,
        )
        changed = await self.session.scalar(
            update(MapViewRow)
            .where(
                MapViewRow.id == revision.view_id,
                MapViewRow.latest_revision_id == base_revision_id,
                MapViewRow.archived.is_(False),
                previous,
                anchor,
            )
            .values(latest_revision_id=revision.id)
            .returning(MapViewRow.id)
            .execution_options(synchronize_session=False)
        )
        if changed is None:
            return False
        self.session.add(row)
        await self.session.flush()
        return True

    async def archive(self, view_id: UUID) -> None:
        await self.session.execute(
            update(MapViewRow).where(MapViewRow.id == view_id).values(archived=True)
        )

    async def delete_for_report(self, report_id: UUID) -> None:
        ids = select(MapViewRow.id).where(MapViewRow.report_id == report_id)
        await self.session.execute(
            delete(MapViewRevisionRow).where(MapViewRevisionRow.view_id.in_(ids))
        )
        await self.session.execute(delete(MapViewRow).where(MapViewRow.report_id == report_id))
