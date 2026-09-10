"""EONET observations retain source extent, time precision and partial coverage caveats."""

from dataclasses import replace
from datetime import timedelta

import httpx
import pytest

from ase.adapters.research.eonet_area import EonetAreaResearchProvider
from ase.domain.events import GeoConfidence, event_id
from ase.domain.evidence_geometry import LocationRole
from ase.domain.research import CollectionStatus
from hazard_area_helpers import ACQUIRED, QUERY, RING, area, hazard, observation
from research_feed_helpers import CLOCK, PublicFeed


def provider(monkeypatch, events):
    feed = PublicFeed(monkeypatch, httpx.Response(200, json={"events": events}))
    return EonetAreaResearchProvider(feed.http, CLOCK), feed


async def test_all_statuses_exact_bbox_date_request_and_original_identity(monkeypatch):
    service, feed = provider(monkeypatch, [hazard(closed=ACQUIRED.isoformat())])
    result = await service.collect(QUERY)
    assert len(feed.guarded) == len(feed.requests) == 1
    request = feed.requests[0]
    assert request.url.host == "eonet.gsfc.nasa.gov"
    assert dict(request.url.params) == {
        "status": "all",
        "start": QUERY.since.date().isoformat(),
        "end": QUERY.until.date().isoformat(),
        "bbox": "0.0,10.0,10.0,0.0",
        "limit": "51",
    }
    assert "authorization" not in request.headers
    assert "private" not in str(request.url).lower()
    item = result.items[0]
    assert item.source_id == "nasa_eonet"
    assert item.id == event_id("nasa_eonet", "EONET_1")
    assert item.observation.acquired_at == ACQUIRED
    assert item.published_at is None
    assert item.geo_confidence is GeoConfidence.EXACT
    assert item.geometry.precision == "source-reported point"
    assert "day-level" in item.observation.limitations
    assert "historical completeness" in result.attempts[0].explanation
    assert "may omit overlapping extents" in result.attempts[0].explanation
    await feed.http.aclose()


async def test_latest_matching_observation_not_latest_outside_date_or_location(monkeypatch):
    service, feed = provider(
        monkeypatch,
        [
            hazard(
                geometry=[
                    observation([3, 3], (ACQUIRED - timedelta(minutes=1)).isoformat()),
                    observation([4, 4], ACQUIRED.isoformat()),
                    observation([20, 20], (ACQUIRED + timedelta(minutes=1)).isoformat()),
                    observation([5, 5], QUERY.until.isoformat()),
                    observation([6, 6], "2026-09-06T11:30:00"),
                ]
            )
        ],
    )
    result = await service.collect(QUERY)
    assert len(result.items) == 1
    assert result.items[0].geometry.to_geometry()["coordinates"] == [4, 4]
    assert result.items[0].observation.acquired_at == ACQUIRED
    await feed.http.aclose()


async def test_intersecting_polygon_keeps_extent_without_invented_centre(monkeypatch):
    polygon = [[[-2, 3], [12, 3], [12, 4], [-2, 4], [-2, 3]]]
    service, feed = provider(monkeypatch, [hazard(geometry=[observation(polygon, kind="Polygon")])])
    item = (await service.collect(QUERY)).items[0]
    assert item.point is None
    assert item.geo_confidence is GeoConfidence.NONE
    assert item.geometry.to_geometry() == {"type": "Polygon", "coordinates": polygon}
    assert item.geometry.location_role is LocationRole.REPORTED_AREA
    assert "not a confirmed impact or fire perimeter" in item.observation.limitations
    await feed.http.aclose()


async def test_hole_exclusion_and_boundary_inclusion(monkeypatch):
    inner = [[[4.5, 4.5], [5.5, 4.5], [5.5, 5.5], [4.5, 5.5], [4.5, 4.5]]]
    service, feed = provider(
        monkeypatch,
        [
            hazard("hole-point", [observation([5, 5])]),
            hazard("hole-polygon", [observation(inner, kind="Polygon")]),
            hazard("boundary", [observation([0, 5])]),
        ],
    )
    query = replace(QUERY, area=area([RING, [[4, 4], [6, 4], [6, 6], [4, 6], [4, 4]]]))
    assert [item.observation.item_id for item in (await service.collect(query)).items] == [
        "boundary"
    ]
    await feed.http.aclose()


@pytest.mark.parametrize(
    "invalid",
    [
        observation(date="not a date"),
        observation([False, 5]),
        observation([181, 5]),
        observation([[[0, 0], [5, 5], [0, 5], [5, 0], [0, 0]]], kind="Polygon"),
        observation([[[179, 0], [-179, 0], [-179, 5], [179, 5], [179, 0]]], kind="Polygon"),
        observation([[1, 1], [2, 2]], kind="LineString"),
    ],
)
async def test_malformed_and_ambiguous_geometry_is_excluded(monkeypatch, invalid):
    service, feed = provider(monkeypatch, [hazard(geometry=[invalid]), hazard("valid")])
    result = await service.collect(QUERY)
    assert [item.observation.item_id for item in result.items] == ["valid"]
    assert "1 candidates excluded" in result.attempts[0].explanation
    await feed.http.aclose()


async def test_unsafe_source_link_falls_back_to_valid_catalogue_link(monkeypatch):
    service, feed = provider(
        monkeypatch,
        [
            hazard(
                sources=[{"url": "http://127.0.0.1/private", "id": "test"}],
                link="https://eonet.gsfc.nasa.gov/api/v3/events/EONET_1",
            )
        ],
    )
    item = (await service.collect(QUERY)).items[0]
    assert item.url == "https://eonet.gsfc.nasa.gov/api/v3/events/EONET_1"
    await feed.http.aclose()


async def test_page_truncation_empty_and_oversized_responses(monkeypatch):
    service, feed = provider(monkeypatch, [hazard(str(index)) for index in range(51)])
    result = await service.collect(QUERY)
    assert len(result.items) == 50
    assert "Truncated page" in result.attempts[0].explanation
    assert len(feed.requests) == 1
    await feed.http.aclose()
    for payload, expected in [([], CollectionStatus.EMPTY), ([{}] * 52, CollectionStatus.FAILED)]:
        service, feed = provider(monkeypatch, payload)
        assert (await service.collect(QUERY)).attempts[0].status is expected
        await feed.http.aclose()


async def test_no_geometries_or_oversized_tracks_not_invented(monkeypatch):
    service, feed = provider(
        monkeypatch,
        [
            hazard("empty", []),
            hazard("large", [observation()] * 257),
            hazard("valid"),
        ],
    )
    assert [item.observation.item_id for item in (await service.collect(QUERY)).items] == ["valid"]
    await feed.http.aclose()


@pytest.mark.parametrize(
    "invalid",
    [
        None,
        {"id": ""},
        hazard(categories=["malformed"]),
        hazard(geometry=[None]),
        hazard(geometry=[observation(date=5)]),
    ],
)
async def test_invalid_event_fields_are_counted_and_do_not_invent_evidence(monkeypatch, invalid):
    service, feed = provider(monkeypatch, [invalid, hazard("valid")])
    result = await service.collect(QUERY)
    assert [item.observation.item_id for item in result.items] == ["valid"]
    assert "1 candidates excluded" in result.attempts[0].explanation
    await feed.http.aclose()


async def test_optional_source_fields_and_capability_are_safe(monkeypatch):
    service, feed = provider(monkeypatch, [hazard(sources=[None])])
    assert service.supports(QUERY)
    assert service.supports_area(QUERY)
    assert not service.supports_area(replace(QUERY, area=None))
    assert (await service.collect(QUERY)).items[0].url is None
    await feed.http.aclose()


async def test_oversized_observation_cannot_hide_in_a_small_event_page(monkeypatch):
    too_many = [[0, 0], *[[1, index / 2000] for index in range(1025)], [0, 0]]
    too_large = [[0, 0], *[[1, 1]] * 6000, [0, 0]]
    service, feed = provider(
        monkeypatch,
        [
            hazard("vertices", [observation([too_many], kind="Polygon")]),
            hazard("bytes", [observation([too_large], kind="Polygon")]),
            hazard("valid"),
        ],
    )
    assert [item.observation.item_id for item in (await service.collect(QUERY)).items] == ["valid"]
    await feed.http.aclose()
