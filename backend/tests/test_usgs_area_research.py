"""Fresh earthquake evidence must preserve scope, source identity and bounded transport."""

import asyncio
from dataclasses import replace
from datetime import timedelta

import httpx
import pytest

from ase.adapters.research.hazard_area import MAX_BODY_BYTES
from ase.adapters.research.usgs_area import SOURCE_ID, UsgsAreaResearchProvider
from ase.domain.events import event_id
from ase.domain.evidence_time import EvidenceTimeBasis
from ase.domain.research import CollectionStatus, ResearchFocus, ResearchMode
from hazard_area_helpers import ACQUIRED, QUERY, RING, area, earthquake
from research_feed_helpers import CLOCK, PublicFeed


def provider(monkeypatch, features):
    feed = PublicFeed(
        monkeypatch, httpx.Response(200, json={"type": "FeatureCollection", "features": features})
    )
    return UsgsAreaResearchProvider(feed.http, CLOCK), feed


async def test_single_guarded_request_original_identity_and_observation_time(monkeypatch):
    service, feed = provider(monkeypatch, [earthquake()])
    result = await service.collect(QUERY)
    assert len(feed.requests) == len(feed.guarded) == 1
    request = feed.requests[0]
    assert request.url.host == "earthquake.usgs.gov"
    assert request.url.params["limit"] == "51"
    assert request.url.params["eventtype"] == "earthquake"
    assert request.url.params["minlongitude"] == "0.0"
    assert "authorization" not in request.headers
    assert "private" not in str(request.url).lower()
    item = result.items[0]
    assert item.id == event_id("usgs_earthquakes", "one")
    assert item.source_id == "usgs_earthquakes"
    assert item.published_at is None
    assert item.observation.acquired_at == ACQUIRED
    assert item.observed_at == CLOCK.now()
    assert item.geometry.to_geometry() == {"type": "Point", "coordinates": [2, 2]}
    assert result.attempts[0].source_id == SOURCE_ID
    assert "complete historical" in result.attempts[0].explanation
    await feed.http.aclose()


async def test_holes_boundaries_dates_and_non_earthquakes_are_excluded(monkeypatch):
    service, feed = provider(
        monkeypatch,
        [
            earthquake("inside"),
            earthquake("hole", [5, 5]),
            earthquake("boundary", [0, 3]),
            earthquake("outside", [20, 20]),
            earthquake("end", acquired=QUERY.until),
            earthquake("start", acquired=QUERY.since),
            earthquake("old", acquired=QUERY.since - timedelta(milliseconds=1)),
            earthquake("blast", type="quarry blast"),
            earthquake("undated", time=None),
            earthquake("boolean", time=True),
            earthquake("impossible", [True, 5]),
        ],
    )
    query = replace(QUERY, area=area([RING, [[4, 4], [6, 4], [6, 6], [4, 6], [4, 4]]]))
    result = await service.collect(query)
    assert {item.observation.item_id for item in result.items} == {"inside", "boundary", "start"}
    assert "8 candidates excluded" in result.attempts[0].explanation
    await feed.http.aclose()


async def test_concave_and_split_antimeridian_areas(monkeypatch):
    service, feed = provider(
        monkeypatch, [earthquake("inside", [1, 1]), earthquake("bbox", [8, 8])]
    )
    query = replace(QUERY, area=area([[[0, 0], [10, 0], [2, 2], [0, 10], [0, 0]]]))
    assert [item.observation.item_id for item in (await service.collect(query)).items] == ["inside"]
    await feed.http.aclose()
    service, feed = provider(
        monkeypatch, [earthquake("east", [175, 5]), earthquake("west", [-175, 5])]
    )
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
    assert len((await service.collect(query)).items) == 2
    assert len(feed.requests) == 1
    await feed.http.aclose()


@pytest.mark.parametrize(
    "changes",
    [
        {"area": None},
        {"focus": ResearchFocus.COMPANY},
        {"country_iso": "GB"},
        {"time_basis": EvidenceTimeBasis.PUBLICATION},
        {"since": QUERY.until - timedelta(days=15)},
    ],
)
async def test_unsupported_scope_makes_no_request(monkeypatch, changes):
    service, feed = provider(monkeypatch, [])
    query = replace(QUERY, **changes)
    assert not service.supports_area(query)
    assert (await service.collect(query)).attempts[0].status is CollectionStatus.UNSUPPORTED
    assert not feed.requests
    await feed.http.aclose()


async def test_page_limit_is_visible_and_never_followed(monkeypatch):
    service, feed = provider(monkeypatch, [earthquake(str(index)) for index in range(51)])
    result = await service.collect(QUERY)
    assert len(result.items) == 50
    assert "Truncated page" in result.attempts[0].explanation
    assert len(feed.requests) == 1
    await feed.http.aclose()
    service, feed = provider(monkeypatch, [earthquake(str(index)) for index in range(101)])
    result = await service.collect(replace(QUERY, mode=ResearchMode.DETAILED))
    assert len(result.items) == 100
    assert feed.requests[0].url.params["limit"] == "101"
    await feed.http.aclose()


@pytest.mark.parametrize(
    "invalid",
    [
        None,
        {"type": "Feature", "id": ""},
        {"type": "Feature", "id": "bad", "geometry": "point", "properties": {}},
        earthquake("bad", [1, 2, 3, 4]),
        earthquake("bad", time=10**100),
    ],
)
async def test_malformed_candidates_do_not_discard_valid_evidence(monkeypatch, invalid):
    service, feed = provider(monkeypatch, [invalid, earthquake()])
    result = await service.collect(QUERY)
    assert [item.observation.item_id for item in result.items] == ["one"]
    assert "1 candidates excluded" in result.attempts[0].explanation
    await feed.http.aclose()


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(302, headers={"Location": "https://example.org/other"}),
        httpx.Response(503, text="private upstream details"),
        httpx.Response(200, content=b"x" * (MAX_BODY_BYTES + 1)),
        httpx.Response(200, content=b"{broken"),
        httpx.Response(200, json={"features": []}),
        httpx.Response(200, json={"type": "FeatureCollection", "features": [{}] * 52}),
    ],
)
async def test_failure_has_no_fallback_or_upstream_details(monkeypatch, response):
    feed = PublicFeed(monkeypatch, response)
    result = await UsgsAreaResearchProvider(feed.http, CLOCK).collect(QUERY)
    assert result.attempts[0].status is CollectionStatus.FAILED
    assert not result.items
    assert "private" not in result.attempts[0].explanation
    assert len(feed.requests) == 1
    await feed.http.aclose()


@pytest.mark.parametrize("error", [TimeoutError, asyncio.CancelledError])
async def test_timeout_is_receipted_but_cancellation_propagates(monkeypatch, error):
    service, feed = provider(monkeypatch, [])

    async def interrupted(*args, **kwargs):
        raise error()

    monkeypatch.setattr(feed.http, "get_bytes", interrupted)
    if error is asyncio.CancelledError:
        with pytest.raises(asyncio.CancelledError):
            await service.collect(QUERY)
    else:
        assert (await service.collect(QUERY)).attempts[0].status is CollectionStatus.TIMED_OUT
    await feed.http.aclose()
