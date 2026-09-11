"""Dated and attributed stationary measurements, without invented area-wide claims."""

from copy import deepcopy
from dataclasses import replace
from datetime import timedelta

import pytest

from ase.adapters.research.openaq_records import SOURCE_ID, OpenAqArea
from ase.domain.events import Category, Point, event_id
from ase.domain.evidence_geometry import LocationRole
from ase.domain.evidence_time import EvidenceTimeBasis
from ase.domain.research import CollectionStatus, ResearchFocus
from hazard_area_helpers import ACQUIRED, QUERY, RING, area
from openaq_helpers import KEY, OpenAqFeed, licence, location, reading
from research_feed_helpers import CLOCK


async def test_original_values_dates_units_provenance_and_licence_are_retained(monkeypatch):
    feed = OpenAqFeed(monkeypatch)
    result = await feed.provider().collect(QUERY)
    assert len(result.items) == 1
    event = result.items[0]
    assert event.id == event_id(SOURCE_ID, f"100:{ACQUIRED.isoformat()}")
    assert event.published_at is None and event.observation.acquired_at == ACQUIRED
    assert event.observed_at == CLOCK.now() and event.category is Category.HUMANITARIAN
    assert event.attributes["value"] == 12.3 and event.attributes["units"] == "µg/m³"
    assert event.attributes["licence_1_dates"] == "2020-01-01 to open-ended"
    assert event.attributes["licence_1_attribution_url"] == "https://owner.example"
    assert "Monitoring provider" in event.summary and "Station owner" in event.summary
    assert "https://opendatacommons.org/licenses/by/1.0/" in event.summary
    assert event.summary.startswith("Dated station value only")
    assert event.geometry.location_role is LocationRole.OBSERVATION_FOOTPRINT
    assert event.geometry.to_geometry()["coordinates"] == [2, 2]
    assert event.grade == "F6" and event.severity is None
    assert len(feed.requests) == len(feed.guarded) == 3
    assert all(request.headers["x-api-key"] == KEY for request in feed.requests)
    assert all(request.url.host == "api.openaq.org" for request in feed.requests)
    assert feed.requests[0].url.params["mobile"] == "false"
    assert feed.requests[0].url.params["limit"] == "100"
    assert feed.requests[1].url.params["datetime_min"] == QUERY.since.isoformat()
    assert all("private" not in str(request.url).lower() for request in feed.requests)
    assert "up to 11 HTTP requests" in result.attempts[0].explanation
    await feed.http.aclose()


async def test_exact_polygon_holes_boundary_and_latest_coordinate_filter(monkeypatch):
    locations = [
        location(1),
        location(2, 5, 5),
        location(3, 0, 3),
        location(4, 20, 20),
        location(5),
    ]
    feed = OpenAqFeed(
        monkeypatch, locations, {1: [reading()], 3: [reading(3, 0, 3)], 5: [reading(5, 5, 5)]}
    )
    query = replace(QUERY, area=area([RING, [[4, 4], [6, 4], [6, 6], [4, 6], [4, 4]]]))
    result = await feed.provider().collect(query)
    assert {event.attributes["station_id"] for event in result.items} == {1, 3}
    assert "3 station/readings excluded" in result.attempts[0].explanation
    await feed.http.aclose()


def test_outward_bbox_rounding_and_split_antimeridian():
    narrow = area(
        [
            [
                [-0.300099, 51.400011],
                [0.100011, 51.400011],
                [0.100011, 51.700011],
                [-0.300099, 51.700011],
                [-0.300099, 51.400011],
            ]
        ]
    )
    assert OpenAqArea(narrow).bbox == "-0.3001,51.4000,0.1001,51.7001"
    split = area(
        [
            [[[170, 0], [180, 0], [180, 10], [170, 10], [170, 0]]],
            [[[-180, 0], [-170, 0], [-170, 10], [-180, 10], [-180, 0]]],
        ],
        "MultiPolygon",
    )
    assert OpenAqArea(split).contains(Point(175, 5))
    assert OpenAqArea(split).contains(Point(-175, 5))
    assert not OpenAqArea(split).contains(Point(0, 5))


@pytest.mark.parametrize(
    "changes",
    [
        {"value": -1},
        {"value": True},
        {"value": "12.3"},
        {"locationsId": 2},
        {"sensorsId": 2},
        {"coordinates": {"latitude": None, "longitude": 2}},
        {"coordinates": {"latitude": 200, "longitude": 2}},
        {"datetime": {"utc": QUERY.until.isoformat()}},
        {"datetime": {"utc": (QUERY.since - timedelta(seconds=1)).isoformat()}},
        {"datetime": {"utc": "2026-09-06T00:00:00"}},
        {"datetime": {}},
    ],
)
async def test_invalid_readings_cannot_gain_freshness_from_station_date(monkeypatch, changes):
    feed = OpenAqFeed(monkeypatch, observations={1: [reading(**changes)]})
    result = await feed.provider().collect(QUERY)
    assert not result.items and result.attempts[0].status is CollectionStatus.EMPTY
    assert len(feed.requests) == 2  # No licence lookup for invalid readings.
    await feed.http.aclose()


async def test_future_measurements_rejected_and_start_inclusive(monkeypatch):
    feed = OpenAqFeed(
        monkeypatch,
        observations={
            1: [
                reading(datetime={"utc": QUERY.since.isoformat()}),
                reading(datetime={"utc": (CLOCK.now() + timedelta(hours=1)).isoformat()}),
            ]
        },
    )
    result = await feed.provider().collect(replace(QUERY, until=CLOCK.now() + timedelta(hours=2)))
    assert [event.observation.acquired_at for event in result.items] == [QUERY.since]
    await feed.http.aclose()


@pytest.mark.parametrize(
    "changes",
    [
        {"isMobile": True},
        {"isMobile": None},
        {"sensors": []},
        {"licenses": []},
        {"id": True},
        {"name": ""},
        {"coordinates": None},
        {"sensors": [{}] * 51},
    ],
)
async def test_unusable_stations_make_no_latest_requests(monkeypatch, changes):
    feed = OpenAqFeed(monkeypatch, [location(**changes)])
    result = await feed.provider().collect(QUERY)
    assert not result.items and len(feed.requests) == 1
    await feed.http.aclose()


@pytest.mark.parametrize(
    "changes",
    [
        {"redistributionAllowed": False},
        {"modificationAllowed": False},
        {"commercialUseAllowed": False},
        {"shareAlikeRequired": True},
        {"attributionRequired": None},
        {"sourceUrl": "http://127.0.0.1/licence"},
    ],
)
async def test_restrictive_or_unknown_licences_excluded_with_honest_receipt(monkeypatch, changes):
    feed = OpenAqFeed(monkeypatch, licences={10: licence(**changes)})
    result = await feed.provider().collect(QUERY)
    assert not result.items and result.attempts[0].status is CollectionStatus.EMPTY
    assert "1 readings excluded by licence" in result.attempts[0].explanation
    await feed.http.aclose()


@pytest.mark.parametrize(
    "change", ["before", "after", "missing-date", "missing-credit", "bad-credit-url"]
)
async def test_licence_must_cover_measurement_date_and_preserve_credit(monkeypatch, change):
    row = location()
    scope = row["licenses"][0]
    if change == "before":
        scope["dateFrom"] = "2027-01-01"
    elif change == "after":
        scope["dateTo"] = "2025-01-01"
    elif change == "missing-date":
        scope["dateFrom"] = None
    elif change == "missing-credit":
        scope["attribution"] = {}
    else:
        scope["attribution"]["url"] = "javascript:bad"
    feed = OpenAqFeed(monkeypatch, [row])
    assert not (await feed.provider().collect(QUERY)).items
    await feed.http.aclose()


async def test_sensor_time_identity_deduplicates_without_merging_distinct_observations(monkeypatch):
    first = reading()
    second = deepcopy(first)
    second["datetime"]["utc"] = (ACQUIRED - timedelta(minutes=1)).isoformat()
    feed = OpenAqFeed(monkeypatch, observations={1: [first, first, second]})
    result = await feed.provider().collect(QUERY)
    assert len(result.items) == 2
    assert len([r for r in feed.requests if "/licenses/" in r.url.path]) == 1
    await feed.http.aclose()


@pytest.mark.parametrize(
    "changes",
    [
        {"area": None},
        {"country_iso": "GB"},
        {"focus": ResearchFocus.COMPANY},
        {"time_basis": EvidenceTimeBasis.PUBLICATION},
        {"since": QUERY.until - timedelta(days=15)},
    ],
)
async def test_unsupported_queries_never_send_private_question(monkeypatch, changes):
    feed = OpenAqFeed(monkeypatch)
    provider = feed.provider()
    query = replace(QUERY, **changes)
    assert not provider.supports_area(query)
    assert (await provider.collect(query)).attempts[0].status is CollectionStatus.UNSUPPORTED
    assert not feed.requests
    await feed.http.aclose()


async def test_missing_key_is_unavailable_without_outbound_requests(monkeypatch):
    feed = OpenAqFeed(monkeypatch)
    result = await feed.provider(None).collect(QUERY)
    assert result.attempts[0].status is CollectionStatus.UNAVAILABLE
    assert not feed.requests
    await feed.http.aclose()


@pytest.mark.parametrize("sensor_id", [True, 1.0])
async def test_sensor_metadata_identifiers_are_strict_integers(monkeypatch, sensor_id):
    row = location()
    row["sensors"][0]["id"] = sensor_id
    feed = OpenAqFeed(monkeypatch, [row], {1: [reading(sensorsId=1)]})
    assert not (await feed.provider().collect(QUERY)).items
    assert len(feed.requests) == 2
    await feed.http.aclose()
