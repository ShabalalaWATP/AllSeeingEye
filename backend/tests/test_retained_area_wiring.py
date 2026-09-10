"""Production research consumes the existing shared public cache and source controls."""

from dataclasses import replace
from datetime import timedelta

import pytest

from ase.adapters.persistence.source_controls import SqlSourceControlRepository
from ase.adapters.research.retained_area import SOURCE_ID
from ase.domain.events import Point
from ase.domain.research import CollectionStatus
from feeds_helpers import make_event
from test_retained_area_feeds import QUERY


@pytest.mark.parametrize("disabled", [False, True])
async def test_container_uses_shared_store_and_underlying_sql_source_admission(
    container, admin, disabled
):
    now = container.clock.now()
    query = replace(QUERY, since=now - timedelta(days=1), until=now, source_ids=(SOURCE_ID,))
    original = make_event(
        source_id="usgs_earthquakes",
        published_at=now - timedelta(minutes=1),
        observed_at=now,
        point=Point(1, 1),
    )
    container.store.upsert([original])
    if disabled:
        async with container.source_admission.guard(), container.session_factory() as session:
            await SqlSourceControlRepository(session).set(original.source_id, False, now, admin.id)
            await session.commit()
    plan = container.research.plan(query)
    assert len(plan.tasks) <= 64
    selected = [task for task in plan.tasks if task.selected]
    assert len(selected) == 1 and selected[0].source_id == SOURCE_ID
    assert selected[0].spatial_supported and selected[0].supported
    result = await container.research.collect(query)
    assert len(result.attempts) == 1
    assert result.items == (() if disabled else (original,))
    assert result.attempts[0].status is (
        CollectionStatus.EMPTY if disabled else CollectionStatus.COMPLETED
    )
    assert container.store.get(original.id) is original
    assert SOURCE_ID not in {
        task.source_id
        for task in container.research.plan(replace(query, area=None, source_ids=None)).tasks
    }
