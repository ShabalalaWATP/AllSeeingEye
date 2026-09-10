"""Legacy EONET display centres cannot become exact area research evidence."""

import json
from dataclasses import replace

import pytest

from ase.adapters.feeds.eonet import EonetConnector
from ase.adapters.research.hazard_area import HazardArea
from ase.adapters.research.retained_area import RetainedAreaFeedProvider
from ase.adapters.store.memory import InMemoryEventStore
from ase.domain.evidence_geometry import EvidenceGeometry, LocationRole
from ase.domain.observation import ObservationMetadata
from hazard_area_helpers import ACQUIRED, QUERY, area, hazard, observation
from research_feed_helpers import CLOCK


async def test_legacy_polygon_average_in_notch_is_not_an_incident_in_the_drawn_area():
    ring = [[0, 0], [10, 0], [10, 10], [6, 10], [6, 4], [4, 4], [4, 10], [0, 10], [0, 0]]
    raw = observation([ring], kind="Polygon")
    legacy = EonetConnector(None, CLOCK)._to_event(hazard(geometry=[raw]), CLOCK.now())
    assert legacy.geometry is None
    query = replace(QUERY, area=area([[[4.2, 5], [4.6, 5], [4.6, 5.6], [4.2, 5.6], [4.2, 5]]]))
    assert HazardArea(query.area).intersecting_geometry(raw, "nasa_eonet", "NASA") is None
    store = InMemoryEventStore()
    store.upsert([legacy])
    result = await RetainedAreaFeedProvider(store).collect(query)
    assert not result.items
    assert "1 scanned candidates excluded" in result.attempts[0].explanation


@pytest.mark.parametrize("validated", [False, True])
async def test_eonet_points_need_original_point_geometry_and_keep_acquisition_time(validated):
    legacy = EonetConnector(None, CLOCK)._to_event(hazard(), CLOCK.now())
    original = EvidenceGeometry(
        json.dumps({"type": "Point", "coordinates": [2, 2]}),
        LocationRole.INCIDENT,
        "source-reported point",
        "Original EONET point",
        "nasa_eonet",
        "NASA",
    )
    event = replace(
        legacy,
        geometry=original if validated else None,
        published_at=None,
        observation=ObservationMetadata(ACQUIRED, "nasa_eonet", "EONET_1", "Source date"),
    )
    store = InMemoryEventStore()
    store.upsert([event])
    result = await RetainedAreaFeedProvider(store).collect(QUERY)
    assert result.items == ((event,) if validated else ())


@pytest.mark.parametrize(
    ("source_id", "role"),
    [("unrelated", LocationRole.INCIDENT), ("nasa_eonet", LocationRole.PROJECT_SITE)],
)
async def test_unrelated_geometry_metadata_cannot_validate_an_eonet_point(source_id, role):
    event = EonetConnector(None, CLOCK)._to_event(hazard(), CLOCK.now())
    geometry = EvidenceGeometry(
        json.dumps({"type": "Point", "coordinates": [2, 2]}),
        role,
        "reported",
        "source geometry",
        source_id,
        "Source",
    )
    store = InMemoryEventStore()
    store.upsert([replace(event, geometry=geometry)])
    assert not (await RetainedAreaFeedProvider(store).collect(QUERY)).items
