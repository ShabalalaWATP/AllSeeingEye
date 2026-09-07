"""Bounded catalogue adapter contracts and observation content identity."""

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from ase.adapters.research_records.copernicus_research import (
    SOURCE_ID,
    CopernicusResearchProvider,
    scene_event,
)
from ase.domain.evidence_geometry import EvidenceGeometry, LocationRole
from ase.domain.footprints import FootprintCollection
from ase.domain.map_geometry import parse_map_geometry
from ase.domain.research import CollectionStatus, ResearchQuery
from ase.domain.research_area import ResearchArea

NOW = datetime(2026, 9, 7, tzinfo=UTC)
RAW = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}
AREA = ResearchArea(
    parse_map_geometry(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [{"type": "Feature", "properties": {"label": "Area"}, "geometry": RAW}],
            }
        )
    )
)
QUERY = ResearchQuery("Inspect this area", NOW - timedelta(days=1), NOW, area=AREA)


def scene(**changes):
    fields = {
        "id": "synthetic-scene",
        "collection": "sentinel-2-l2a",
        "captured_at": NOW - timedelta(hours=1),
        "cloud_cover": 12.0,
        "source_url": "https://example.test/scene",
        "licence": "Synthetic licence",
        "licence_url": "https://example.test/licence",
        "source_geometry": EvidenceGeometry(
            json.dumps(RAW),
            LocationRole.OBSERVATION_FOOTPRINT,
            "Scene coverage",
            "Catalogue geometry",
            SOURCE_ID,
            "Synthetic catalogue",
        ),
    }
    return SimpleNamespace(**(fields | changes))


class Catalogue:
    def __init__(self, result):
        self.result = result
        self.calls = []

    async def search(self, query):
        self.calls.append(query)
        return self.result


def test_scene_preserves_unknown_publication_and_content_changes():
    original = scene_event(scene(), NOW)
    assert original.published_at is None and original.point is None
    assert original.observation.acquired_at == NOW - timedelta(hours=1)
    assert original.geometry.to_geometry() == RAW
    assert original.content_hash == scene_event(scene(), NOW + timedelta(days=1)).content_hash
    for changed in (
        scene(cloud_cover=13),
        scene(captured_at=NOW - timedelta(hours=2)),
        scene(licence="Changed licence"),
        scene(
            source_geometry=replace(
                scene().source_geometry,
                source_geometry=json.dumps(
                    {
                        "type": "Polygon",
                        "coordinates": [[[0, 0], [2, 0], [2, 1], [0, 1], [0, 0]]],
                    }
                ),
            )
        ),
    ):
        assert scene_event(changed, NOW).content_hash != original.content_hash


async def test_one_request_preserves_truncation_and_original_geometry():
    catalogue = Catalogue(FootprintCollection((scene(),), "completed", True, "Metadata only", NOW))
    result = await CopernicusResearchProvider(catalogue).collect(QUERY)
    assert len(catalogue.calls) == 1
    assert catalogue.calls[0].bbox == (0, 0, 1, 1)
    assert catalogue.calls[0].since == QUERY.since
    assert catalogue.calls[0].until == QUERY.until
    assert result.items[0].published_at is None
    assert result.attempts[0].status == CollectionStatus.COMPLETED
    assert "truncated" in result.attempts[0].explanation


@pytest.mark.parametrize(
    "query", [replace(QUERY, area=None), replace(QUERY, since=NOW - timedelta(days=15))]
)
async def test_unsupported_scope_never_calls_catalogue(query):
    catalogue = Catalogue(None)
    result = await CopernicusResearchProvider(catalogue).collect(query)
    assert not catalogue.calls and not result.items
    assert result.attempts[0].status == CollectionStatus.UNSUPPORTED


@pytest.mark.parametrize("status", ["empty", "unavailable"])
async def test_empty_and_unavailable_are_distinct(status):
    catalogue = Catalogue(FootprintCollection((), status, False, "Catalogue receipt", NOW))
    result = await CopernicusResearchProvider(catalogue).collect(QUERY)
    assert result.attempts[0].status.value == status
    assert not result.items


async def test_missing_original_geometry_rejects_whole_page():
    catalogue = Catalogue(
        FootprintCollection(
            (scene(), scene(source_geometry=None)), "completed", False, "Metadata", NOW
        )
    )
    result = await CopernicusResearchProvider(catalogue).collect(QUERY)
    assert not result.items
    assert result.attempts[0].status == CollectionStatus.UNAVAILABLE


async def test_oversized_catalogue_page_does_not_release_partial_results():
    catalogue = Catalogue(
        FootprintCollection(
            tuple(scene(id=f"scene-{index}") for index in range(21)),
            "completed",
            True,
            "Metadata",
            NOW,
        )
    )
    result = await CopernicusResearchProvider(catalogue).collect(QUERY)
    assert not result.items
    assert result.attempts[0].status == CollectionStatus.UNAVAILABLE
