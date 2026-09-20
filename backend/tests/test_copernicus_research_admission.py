"""Catalogue composition respects the source admission boundary."""

import asyncio
from contextlib import asynccontextmanager

from ase.adapters.research_records.copernicus_research import SOURCE_ID, CopernicusResearchProvider
from ase.application.research.source_admission import ControlledResearchProvider
from ase.domain.footprints import FootprintCollection
from ase.domain.research import CollectionStatus
from test_copernicus_research import NOW, QUERY, Catalogue, scene


class Admission:
    def __init__(self, enabled):
        self.active = enabled
        self.lock = asyncio.Lock()

    async def enabled(self, source_id):
        assert source_id == SOURCE_ID
        return self.active

    @asynccontextmanager
    async def guard(self):
        async with self.lock:
            yield


async def test_disabled_catalogue_never_calls_underlying_provider():
    catalogue = Catalogue(None)
    provider = ControlledResearchProvider(CopernicusResearchProvider(catalogue), Admission(False))
    result = await provider.collect(QUERY)
    assert not catalogue.calls and not result.items
    assert result.attempts[0].status == CollectionStatus.UNAVAILABLE


async def test_source_disabled_during_collection_discards_scene_evidence():
    entered, release = asyncio.Event(), asyncio.Event()

    class PendingCatalogue:
        async def search(self, query):
            entered.set()
            await release.wait()
            return FootprintCollection((scene(),), "completed", False, "Metadata only", NOW)

    admission = Admission(True)
    provider = ControlledResearchProvider(CopernicusResearchProvider(PendingCatalogue()), admission)
    task = asyncio.create_task(provider.collect(QUERY))
    try:
        await asyncio.wait_for(entered.wait(), timeout=2)
        async with admission.guard():
            admission.active = False
        release.set()
        result = await asyncio.wait_for(task, timeout=2)
        assert not result.items
        assert result.attempts[0].status == CollectionStatus.UNAVAILABLE
    finally:
        if not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)


def test_source_wrapper_retains_spatial_capability_and_limits():
    provider = ControlledResearchProvider(
        CopernicusResearchProvider(Catalogue(None)), Admission(True)
    )
    assert provider.supports_area(QUERY)
    assert "10 degrees" in provider.capabilities.spatial_scope
    assert "14 days" in provider.capabilities.temporal_scope
