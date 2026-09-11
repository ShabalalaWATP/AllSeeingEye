"""OpenAQ deadlines, pagination, quotas, authentication and cancellation boundaries."""

import asyncio
from dataclasses import replace
from datetime import timedelta

import httpx
import pytest

from ase.adapters.research import openaq_area
from ase.adapters.research.openaq_client import (
    FAILURE_COOLDOWN,
    HOURLY_ALLOWANCE,
    MAX_BODY_BYTES,
    OpenAqAllowanceError,
)
from ase.domain.research import CollectionStatus, ResearchMode
from hazard_area_helpers import ACQUIRED, QUERY
from openaq_helpers import KEY, OpenAqFeed, licence, location, reading


async def test_newest_station_metadata_prioritised_without_changing_measurement_dates(monkeypatch):
    locations = [
        location(i, datetimeLast={"utc": (ACQUIRED - timedelta(days=10)).isoformat()})
        for i in range(1, 100)
    ]
    locations.append(location(100))
    feed = OpenAqFeed(monkeypatch, locations, {100: [reading(100)]})
    result = await feed.provider().collect(QUERY)
    assert len(result.items) == 1 and result.items[0].attributes["station_id"] == 100
    latest = [r for r in feed.requests if r.url.path.endswith("/latest")]
    assert len(latest) == 3 and latest[0].url.path == "/v3/locations/100/latest"
    assert "page truncated" in result.attempts[0].explanation
    assert all(r.url.params.get("page", "1") == "1" for r in feed.requests)
    await feed.http.aclose()


async def test_detailed_station_and_unique_licence_budget_caps_requests(monkeypatch):
    locations = [location(i) for i in range(1, 9)]
    for row in locations:
        row["licenses"][0]["id"] = row["id"] + 10
    feed = OpenAqFeed(
        monkeypatch,
        locations,
        {i: [reading(i)] for i in range(1, 9)},
        {i + 10: licence(i + 10) for i in range(1, 9)},
    )
    result = await feed.provider().collect(replace(QUERY, mode=ResearchMode.DETAILED))
    assert len(result.items) == 4
    assert len(feed.requests) == 11
    assert len([r for r in feed.requests if r.url.path.endswith("/latest")]) == 6
    assert len([r for r in feed.requests if "/licenses/" in r.url.path]) == 4
    assert "2 readings excluded by licence checks/budget" in result.attempts[0].explanation
    await feed.http.aclose()


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(302, headers={"Location": "https://evil.example/steal"}),
        httpx.Response(429, text="private provider response"),
        httpx.Response(200, content=b"{"),
        httpx.Response(200, content=b"x" * (MAX_BODY_BYTES + 1)),
        httpx.Response(200, json={"results": [{}] * 101}),
        httpx.Response(200, json={}),
    ],
)
async def test_unusable_response_never_follows_redirects_retries_or_leaks(monkeypatch, response):
    feed = OpenAqFeed(monkeypatch, response=lambda request: response)
    result = await feed.provider().collect(QUERY)
    assert result.attempts[0].status is CollectionStatus.FAILED and not result.items
    assert len(feed.requests) == 1
    assert KEY not in repr(result) and "private provider" not in repr(result)
    await feed.http.aclose()


async def test_failure_cooldown_shared_between_runs_and_recovers(monkeypatch):
    feed = OpenAqFeed(monkeypatch, response=lambda request: httpx.Response(429))
    provider = feed.provider()
    assert (await provider.collect(QUERY)).attempts[0].status is CollectionStatus.FAILED
    assert (await provider.collect(QUERY)).attempts[0].status is CollectionStatus.BUDGET_EXHAUSTED
    assert len(feed.requests) == 1
    feed.time += FAILURE_COOLDOWN
    feed.response = None
    assert (await provider.collect(QUERY)).items
    await feed.http.aclose()


async def test_quota_pacing_and_expiry_remain_shared_across_calls(monkeypatch):
    feed = OpenAqFeed(monkeypatch)
    client = feed.provider()._client
    await asyncio.gather(client.get("/v3/locations"), client.get("/v3/locations"))
    assert list(client._requests) == [0, 2]
    client._requests.extend([2] * (HOURLY_ALLOWANCE - 2))
    with pytest.raises(OpenAqAllowanceError):
        await client.get("/v3/locations")
    assert len(feed.requests) == 2
    feed.time = 3602
    await client.get("/v3/locations")
    assert len(client._requests) == 1
    await feed.http.aclose()


@pytest.mark.parametrize("error", [TimeoutError, ValueError])
async def test_failure_after_success_retains_partial_evidence(monkeypatch, error):
    feed = OpenAqFeed(monkeypatch, [location(), location(2)])
    provider = feed.provider()
    original = provider._client.get

    async def fail_second(path):
        if "/locations/2/latest" in path:
            raise error("private response")
        return await original(path)

    monkeypatch.setattr(provider._client, "get", fail_second)
    result = await provider.collect(QUERY)
    assert len(result.items) == 1
    assert result.attempts[0].status is CollectionStatus.COMPLETED
    assert "Partial results retained" in result.attempts[0].explanation
    assert "private response" not in repr(result)
    await feed.http.aclose()


async def test_own_deadline_returns_before_collector_deadline(monkeypatch):
    feed = OpenAqFeed(monkeypatch)
    provider = feed.provider()
    timeout = asyncio.timeout
    durations = []

    def shortened(seconds):
        durations.append(seconds)
        return timeout(0.01)

    async def pending(path):
        await asyncio.Future()

    monkeypatch.setattr(openaq_area.asyncio, "timeout", shortened)
    monkeypatch.setattr(provider._client, "get", pending)
    result = await provider.collect(QUERY)
    assert result.attempts[0].status is CollectionStatus.TIMED_OUT
    assert durations == [10]
    await feed.http.aclose()


async def test_cancellation_propagates_without_refunding_request(monkeypatch):
    feed = OpenAqFeed(monkeypatch)
    provider = feed.provider()

    async def cancelled(*args, **kwargs):
        raise asyncio.CancelledError()

    monkeypatch.setattr(feed.http, "get_bytes", cancelled)
    with pytest.raises(asyncio.CancelledError):
        await provider.collect(QUERY)
    assert len(provider._client._requests) == 1
    await feed.http.aclose()


@pytest.mark.parametrize("key", ["bad\nkey", "with space", "x" * 513, "ünicode"])
async def test_invalid_key_rejected_without_exposing_it(monkeypatch, key):
    feed = OpenAqFeed(monkeypatch)
    with pytest.raises(ValueError, match="Invalid OpenAQ") as error:
        feed.provider(key)
    assert key not in str(error.value)
    await feed.http.aclose()
