"""Spatial catalogue records pass through collection planning and filtering."""

from dataclasses import replace
from datetime import timedelta

from ase.adapters.research_records.copernicus_research import SOURCE_ID, CopernicusResearchProvider
from ase.application.research.service import ResearchCollectionService
from ase.domain.footprints import FootprintCollection
from ase.domain.research import CollectionStatus
from test_copernicus_research import NOW, QUERY, Catalogue, scene


async def test_explicit_source_selection_and_acquisition_filtering():
    catalogue = Catalogue(
        FootprintCollection(
            (
                scene(id="in-window"),
                scene(id="outside", captured_at=QUERY.since - timedelta(seconds=1)),
            ),
            "completed",
            False,
            "Metadata",
            NOW,
        )
    )
    provider = CopernicusResearchProvider(catalogue)
    service = ResearchCollectionService(lambda _: [provider])
    selected = replace(QUERY, source_ids=(SOURCE_ID,))
    preview = service.plan(selected)
    assert not catalogue.calls
    assert preview.tasks[0].spatial_supported and preview.tasks[0].selected
    result = await service.collect(selected)
    assert len(catalogue.calls) == 1 and len(result.items) == 1
    assert result.items[0].observation.item_id == "in-window"
    assert result.items[0].published_at is None
    assert result.attempts[0].status == CollectionStatus.COMPLETED
    assert result.attempts[0].result_count == 1


async def test_unselected_catalogue_has_no_collection_or_outbound_request():
    catalogue = Catalogue(None)
    service = ResearchCollectionService(lambda _: [CopernicusResearchProvider(catalogue)])
    result = await service.collect(replace(QUERY, source_ids=()))
    assert not result.items and not result.attempts and not catalogue.calls


async def test_nonspatial_request_is_explicitly_unsupported():
    catalogue = Catalogue(None)
    service = ResearchCollectionService(lambda _: [CopernicusResearchProvider(catalogue)])
    result = await service.collect(replace(QUERY, area=None, source_ids=(SOURCE_ID,)))
    assert not result.items and not catalogue.calls
    assert result.attempts[0].status == CollectionStatus.UNSUPPORTED
