"""Deleting the parent report cannot leave saved private map geometry behind."""

from sqlalchemy import func, select

from ase.adapters.persistence.map_view_models import MapViewRevisionRow, MapViewRow
from test_map_view_repository import seed


async def test_report_deletion_removes_saved_view_and_immutable_revisions(container, user):
    view, _ = await seed(container, user)
    async with container.session_factory() as session:
        await container.repositories(session).reports.delete(view.report_id)
        await session.commit()
    async with container.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(MapViewRow)) == 0
        assert await session.scalar(select(func.count()).select_from(MapViewRevisionRow)) == 0
