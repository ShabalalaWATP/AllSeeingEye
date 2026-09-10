"""Area evidence is precise, bounded, source-attributed and honest about retained coverage."""

import asyncio
import json
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import timedelta

import pytest

from ase.adapters.research.retained_area import SOURCE_ID, RetainedAreaFeedProvider
from ase.adapters.research.retained_area_selection import SCAN_PER_CATEGORY
from ase.adapters.store.memory import InMemoryEventStore
from ase.domain.events import Category, GeoConfidence, Point
from ase.domain.evidence_geometry import EvidenceGeometry, LocationRole
from ase.domain.evidence_time import EvidenceTimeBasis
from ase.domain.map_geometry import parse_map_geometry
from ase.domain.observation import ObservationMetadata
from ase.domain.research import CollectionStatus, ResearchFocus, ResearchMode, ResearchQuery
from ase.domain.research_area import ResearchArea
from feeds_helpers import NOW, make_event

RING = [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]


def area(coordinates=None, kind="Polygon"):
    return ResearchArea(
        parse_map_geometry(
            json.dumps(
                {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "geometry": {"type": kind, "coordinates": coordinates or [RING]},
                        }
                    ],
                }
            )
        )
    )


QUERY = ResearchQuery(
    "What is happening here?",
    since=NOW - timedelta(days=1),
    until=NOW + timedelta(minutes=1),
    area=area(),
)


def event(key="inside", **kwargs):
    return make_event(key, point=Point(1, 1), **kwargs)


class Admission:
    def __init__(self):
        self.disabled = set()
        self.in_guard = False

    @asynccontextmanager
    async def guard(self):
        assert not self.in_guard
        self.in_guard = True
        try:
            yield
        finally:
            self.in_guard = False

    async def enabled(self, source_id):
        return source_id not in self.disabled

    async def enabled_many(self, source_ids):
        assert self.in_guard
        return {source_id: source_id not in self.disabled for source_id in source_ids}


@pytest.mark.parametrize("focus", [ResearchFocus.COMPANY, ResearchFocus.DOMAIN])
async def test_capability_is_area_general_only(focus):
    provider = RetainedAreaFeedProvider(InMemoryEventStore())
    assert provider.supports_area(QUERY)
    assert not provider.supports(replace(QUERY, area=None))
    assert not provider.supports(replace(QUERY, focus=focus))
    assert not provider.supports(replace(QUERY, time_basis=EvidenceTimeBasis.PUBLICATION))
    result = await provider.collect(replace(QUERY, area=None))
    assert result.attempts[0].status is CollectionStatus.UNSUPPORTED


async def test_exact_polygon_holes_boundaries_and_original_identity():
    store = InMemoryEventStore()
    original = event(source_id="usgs_earthquakes")
    boundary = replace(event("boundary"), point=Point(10, 5))
    hole = replace(event("hole"), point=Point(5, 5))
    outside = replace(event("outside"), point=Point(11, 2))
    approximate = replace(event("approximate"), geo_confidence=GeoConfidence.CITY)
    unknown = replace(event("unknown"), point=None, geo_confidence=GeoConfidence.NONE)
    store.upsert([original, boundary, hole, outside, approximate, unknown])
    query = replace(QUERY, area=area([RING, [[4, 4], [6, 4], [6, 6], [4, 6], [4, 4]]]))
    result = await RetainedAreaFeedProvider(store).collect(query)
    assert {item.id for item in result.items} == {original.id, boundary.id}
    assert next(item for item in result.items if item.id == original.id) is original
    receipt = result.attempts[0]
    assert receipt.source_id == SOURCE_ID
    assert "2 original sources" in receipt.explanation
    assert "disaster 2" in receipt.explanation
    assert "not a fresh external search" in receipt.explanation
    assert "not guaranteed current" in receipt.explanation
    assert store.stats().total == 6


async def test_concave_polygon_does_not_substitute_bbox():
    store = InMemoryEventStore()
    original = event()
    outside = replace(event("bbox-only"), point=Point(8, 8))
    store.upsert([original, outside])
    query = replace(QUERY, area=area([[[0, 0], [10, 0], [2, 2], [0, 10], [0, 0]]]))
    assert (await RetainedAreaFeedProvider(store).collect(query)).items == (original,)


async def test_split_seam_multipolygon_covers_both_sides_without_middle():
    query = replace(
        QUERY,
        area=area(
            [
                [[[170, 0], [180, 0], [180, 10], [170, 10], [170, 0]]],
                [[[-180, 0], [-170, 0], [-170, 10], [-180, 10], [-180, 0]]],
            ],
            "MultiPolygon",
        ),
    )
    store = InMemoryEventStore()
    west = replace(event("west"), point=Point(-175, 5))
    east = replace(event("east"), point=Point(175, 5))
    store.upsert([west, east, event("middle")])
    result = await RetainedAreaFeedProvider(store).collect(query)
    assert {item.id for item in result.items} == {west.id, east.id}


@pytest.mark.parametrize(
    "confidence",
    [GeoConfidence.CITY, GeoConfidence.ADMIN1, GeoConfidence.COUNTRY, GeoConfidence.NONE],
)
async def test_approximate_representative_points_never_establish_area_membership(confidence):
    store = InMemoryEventStore()
    store.upsert([replace(event(), geo_confidence=confidence)])
    result = await RetainedAreaFeedProvider(store).collect(QUERY)
    assert not result.items
    assert result.attempts[0].status is CollectionStatus.EMPTY
    assert "do not establish absence" in result.attempts[0].explanation


@pytest.mark.parametrize(
    ("role", "geometry"),
    [
        (LocationRole.OBSERVATION_FOOTPRINT, {"type": "Point", "coordinates": [1, 1]}),
        (LocationRole.PUBLISHER_LOCATION, {"type": "Point", "coordinates": [1, 1]}),
        (LocationRole.INCIDENT, {"type": "Polygon", "coordinates": [RING]}),
        (LocationRole.INCIDENT, {"type": "Point", "coordinates": [2, 2]}),
    ],
)
async def test_source_footprints_or_other_location_roles_are_not_incident_points(role, geometry):
    store = InMemoryEventStore()
    source = EvidenceGeometry(json.dumps(geometry), role, "reported", "source", "test", "Test")
    store.upsert([replace(event(), geometry=source)])
    assert not (await RetainedAreaFeedProvider(store).collect(QUERY)).items


async def test_acquisition_time_takes_precedence_and_interval_is_half_open():
    store = InMemoryEventStore()
    acquired = replace(
        event("acquired"),
        published_at=NOW - timedelta(days=5),
        observation=ObservationMetadata(NOW, "sensor", "acquired", "Point observation"),
    )
    old_observation = replace(
        event("old-observation"),
        observation=ObservationMetadata(
            NOW - timedelta(days=5), "sensor", "old-observation", "Point observation"
        ),
    )
    start = replace(event("start"), published_at=QUERY.since)
    end = replace(event("end"), published_at=QUERY.until)
    unknown = replace(event("unknown"), published_at=None)
    store.upsert([acquired, old_observation, start, end, unknown])
    result = await RetainedAreaFeedProvider(store).collect(QUERY)
    assert {item.id for item in result.items} == {acquired.id, start.id}


@pytest.mark.parametrize(
    ("mode", "per_category"), [(ResearchMode.QUICK, 8), (ResearchMode.DETAILED, 24)]
)
async def test_category_and_original_source_fairness_leaves_budget_for_external_sources(
    mode, per_category
):
    store = InMemoryEventStore()
    for category in Category:
        store.upsert(
            [event(f"{category}-{i}", category=category, source_id="busy") for i in range(40)]
            + [event(f"{category}-sparse", category=category, source_id="sparse")]
        )
    result = await RetainedAreaFeedProvider(store).collect(replace(QUERY, mode=mode))
    assert len(result.items) == per_category * len(Category)
    for category in Category:
        assert sum(item.category is category for item in result.items) == per_category
        assert any(
            item.category is category and item.source_id == "sparse" for item in result.items
        )
    assert "truncated" in result.attempts[0].explanation


async def test_source_disabled_during_cooperative_read_is_excluded_before_release(monkeypatch):
    admission = Admission()
    store = InMemoryEventStore()
    store.upsert([event(source_id="disabled"), event("allowed", source_id="allowed")])
    read = store.read_cooperatively

    async def read_then_disable(query, project):
        value = await read(query, project)
        admission.disabled.add("disabled")
        return value

    monkeypatch.setattr(store, "read_cooperatively", read_then_disable)
    result = await RetainedAreaFeedProvider(store, admission=admission).collect(QUERY)
    assert [item.source_id for item in result.items] == ["allowed"]
    assert "1 disabled-source records excluded" in result.attempts[0].explanation
    assert not admission.in_guard


async def test_static_disable_and_capability_disable(monkeypatch):
    store = InMemoryEventStore()
    store.upsert([event(source_id="blocked")])
    provider = RetainedAreaFeedProvider(store, disabled=("blocked",))
    assert not (await provider.collect(QUERY)).items
    admission = Admission()
    admission.disabled.add(SOURCE_ID)

    async def forbidden(*args):
        pytest.fail("Disabled provider read the event store")

    monkeypatch.setattr(store, "read_cooperatively", forbidden)
    result = await RetainedAreaFeedProvider(store, admission=admission).collect(QUERY)
    assert result.attempts[0].status is CollectionStatus.UNAVAILABLE


async def test_scan_bound_and_cooperative_store_path(monkeypatch):
    store = InMemoryEventStore()
    store.upsert([event(str(i)) for i in range(SCAN_PER_CATEGORY + 10)])

    def sync_forbidden(*args):
        pytest.fail("Production store selection ran on the event loop")

    monkeypatch.setattr(store, "query", sync_forbidden)
    result = await RetainedAreaFeedProvider(store).collect(QUERY)
    assert len(result.items) == 8
    assert "truncated" in result.attempts[0].explanation


async def test_cancellation_stops_before_scanning_other_categories(monkeypatch):
    store = InMemoryEventStore()
    entered = asyncio.Event()
    queries = []

    async def pause(query, project):
        queries.append(query)
        entered.set()
        await asyncio.Event().wait()

    monkeypatch.setattr(store, "read_cooperatively", pause)
    task = asyncio.create_task(RetainedAreaFeedProvider(store).collect(QUERY))
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert len(queries) == 1


async def test_valid_original_incident_point_and_static_sensor_family_disable():
    store = InMemoryEventStore()
    geometry = EvidenceGeometry(
        '{"type":"Point","coordinates":[1,1]}',
        LocationRole.INCIDENT,
        "reported point",
        "sensor",
        "sensor",
        "Sensor data",
    )
    accepted = replace(event("precise"), geometry=geometry)
    blocked = event("variant", source_id="firms_viirs_noaa21")
    store.upsert([accepted, blocked])
    result = await RetainedAreaFeedProvider(store, disabled=("firms_viirs_noaa20",)).collect(QUERY)
    assert result.items == (accepted,)
    assert "No admitted records: news, conflict" in result.attempts[0].explanation


async def test_invalid_multipolygon_is_unsupported_without_bbox_fallback():
    store = InMemoryEventStore()
    store.upsert([event()])
    query = replace(QUERY, area=area([[RING], [RING]], "MultiPolygon"))
    result = await RetainedAreaFeedProvider(store).collect(query)
    assert not result.items and result.attempts[0].status is CollectionStatus.UNSUPPORTED
    assert "No envelope search" in result.attempts[0].explanation


async def test_disabling_whole_capability_during_read_blocks_final_release(monkeypatch):
    store, admission = InMemoryEventStore(), Admission()
    store.upsert([event()])
    read = store.read_cooperatively

    async def disable_after_read(query, project):
        result = await read(query, project)
        admission.disabled.add(SOURCE_ID)
        return result

    monkeypatch.setattr(store, "read_cooperatively", disable_after_read)
    result = await RetainedAreaFeedProvider(store, admission=admission).collect(QUERY)
    assert result.attempts[0].status is CollectionStatus.UNAVAILABLE
    assert not result.items
