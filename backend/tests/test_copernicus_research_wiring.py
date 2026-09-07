"""Production composition uses persisted admission for catalogue evidence."""

from dataclasses import replace
from datetime import timedelta

import pytest

from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.persistence.source_controls import SqlSourceControlRepository
from ase.adapters.research_records.copernicus_research import SOURCE_ID
from ase.domain.research import CollectionStatus
from test_copernicus_research import QUERY
from test_copernicus_research_geometry import payload


@pytest.mark.parametrize("disable_at", ["before", "during", "never"])
async def test_container_catalogue_honours_persisted_activation(
    container, admin, monkeypatch, disable_at
):
    now = container.clock.now()
    query = replace(QUERY, since=now - timedelta(days=1), until=now, source_ids=(SOURCE_ID,))
    calls = []

    async def disable():
        async with container.source_admission.guard(), container.session_factory() as session:
            await SqlSourceControlRepository(session).set(SOURCE_ID, False, now, admin.id)
            await session.commit()

    async def get_json(self, url, **kwargs):
        calls.append(url)
        if disable_at == "during":
            await disable()
        data = payload()
        data["features"][0]["properties"]["datetime"] = (now - timedelta(hours=1)).isoformat()
        return data

    monkeypatch.setattr(FeedHttpClient, "get_json", get_json)
    if disable_at == "before":
        await disable()
    task = next(
        task for task in container.research.plan(query).tasks if task.source_id == SOURCE_ID
    )
    assert task.selected and task.spatial_supported
    assert not calls
    result = await container.research.collect(query)
    assert len(calls) == (0 if disable_at == "before" else 1)
    assert container.store.stats().total == 0
    if disable_at == "never":
        assert len(result.items) == 1
        assert result.items[0].geometry is not None
        assert result.items[0].published_at is None
        assert result.attempts[0].status == CollectionStatus.COMPLETED
    else:
        assert not result.items
        assert result.attempts[0].status == CollectionStatus.UNAVAILABLE
