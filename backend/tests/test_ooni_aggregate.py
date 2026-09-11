"""Country aggregate fixtures only; no individual probe records or live network."""

import json
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import httpx
import pytest

from ase.adapters.research_records.ooni import MAX_JSON_BYTES, OoniAggregateProvider
from ase.domain.events import GeoConfidence
from ase.domain.research import CollectionStatus
from research_feed_helpers import CLOCK, QUERY, PublicFeed

FIXTURE = Path(__file__).parent / "fixtures" / "research" / "ooni_aggregate.json"
OONI_QUERY = replace(QUERY, subject="ooni:IR", country_iso="IR")


def payload() -> dict:
    return json.loads(FIXTURE.read_text("utf-8"))


async def test_country_counters_no_probe_data_and_no_private_query_leak(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = payload()
    data["result"][0]["probe_ip"] = "synthetic-redacted-marker"
    feed = PublicFeed(monkeypatch, httpx.Response(200, json=data))
    result = await OoniAggregateProvider(feed.http, CLOCK, allow_noncommercial_data=True).collect(
        OONI_QUERY
    )
    await feed.http.aclose()
    assert len(feed.requests) == 1
    request = feed.requests[0]
    assert request.url.host == "api.ooni.io" and request.url.path == "/api/v1/aggregation"
    assert set(request.url.params) == {
        "probe_cc",
        "test_name",
        "since",
        "until",
        "axis_x",
        "time_grain",
    }
    assert request.url.params["probe_cc"] == "IR"
    assert OONI_QUERY.question not in str(request.url) and OONI_QUERY.terms[0] not in str(
        request.url
    )
    event = result.items[0]
    assert event.point is None and event.country_iso == "IR"
    assert event.geo_confidence is GeoConfidence.COUNTRY and event.grade == "F6"
    assert event.attributes["measurement_count"] == 100
    assert event.attributes["anomaly_count"] == 15
    assert event.attributes["period_start"] == QUERY.since.isoformat()
    assert "probe_ip" not in event.attributes and "synthetic-redacted-marker" not in str(event)
    assert "CC BY-NC-SA" in event.summary
    assert "false positives" in result.attempts[0].explanation


async def test_licence_acknowledgement_required_before_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    feed = PublicFeed(monkeypatch, httpx.Response(200, json=payload()))
    result = await OoniAggregateProvider(feed.http, CLOCK).collect(OONI_QUERY)
    await feed.http.aclose()
    assert result.attempts[0].status is CollectionStatus.UNAVAILABLE and not feed.requests


@pytest.mark.parametrize(
    "query",
    [
        QUERY,
        replace(OONI_QUERY, country_iso="RU", country_isos=()),
        replace(OONI_QUERY, subject="ooni:IR,US"),
        replace(OONI_QUERY, until=QUERY.since + timedelta(days=15)),
    ],
)
async def test_unsupported_target_or_window_does_not_request(
    monkeypatch: pytest.MonkeyPatch, query
) -> None:
    feed = PublicFeed(monkeypatch, httpx.Response(200, json=payload()))
    result = await OoniAggregateProvider(feed.http, CLOCK, allow_noncommercial_data=True).collect(
        query
    )
    await feed.http.aclose()
    assert result.attempts[0].status is CollectionStatus.UNSUPPORTED and not feed.requests


async def test_explicit_selection_with_country_is_supported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    feed = PublicFeed(monkeypatch, httpx.Response(200, json=payload()))
    provider = OoniAggregateProvider(feed.http, CLOCK, allow_noncommercial_data=True)
    query = replace(QUERY, source_ids=(provider.id,), country_iso="IR")
    assert provider.supports(query)
    assert (await provider.collect(query)).attempts[0].status is CollectionStatus.COMPLETED
    await feed.http.aclose()


@pytest.mark.parametrize(
    "mutation",
    ["negative", "boolean", "denominator", "duplicate", "out_of_window", "dimension", "too_many"],
)
async def test_invalid_aggregate_is_failed_not_empty(
    monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    data = payload()
    if mutation == "negative":
        data["result"][0]["anomaly_count"] = -1
    if mutation == "boolean":
        data["result"][0]["anomaly_count"] = True
    if mutation == "denominator":
        data["result"][0]["measurement_count"] = 101
    if mutation == "duplicate":
        data["result"] *= 2
    if mutation == "out_of_window":
        data["result"][0]["measurement_start_day"] = "2026-01-01"
    if mutation == "dimension":
        data["dimension_count"] = 2
    if mutation == "too_many":
        data["result"] *= 16
    feed = PublicFeed(monkeypatch, httpx.Response(200, json=data))
    result = await OoniAggregateProvider(feed.http, CLOCK, allow_noncommercial_data=True).collect(
        OONI_QUERY
    )
    await feed.http.aclose()
    assert result.attempts[0].status is CollectionStatus.FAILED and not result.items


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(403),
        httpx.Response(200, text="<html />"),
        httpx.Response(200, content=b" " * (MAX_JSON_BYTES + 1)),
    ],
)
async def test_failures_and_byte_ceiling(
    monkeypatch: pytest.MonkeyPatch, response: httpx.Response
) -> None:
    feed = PublicFeed(monkeypatch, response)
    result = await OoniAggregateProvider(feed.http, CLOCK, allow_noncommercial_data=True).collect(
        OONI_QUERY
    )
    await feed.http.aclose()
    assert result.attempts[0].status is CollectionStatus.FAILED


async def test_empty_and_zero_counts_are_no_returned_coverage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = payload()
    for key in tuple(data["result"][0]):
        if key.endswith("count"):
            data["result"][0][key] = 0
    feed = PublicFeed(monkeypatch, httpx.Response(200, json=data))
    result = await OoniAggregateProvider(feed.http, CLOCK, allow_noncommercial_data=True).collect(
        OONI_QUERY
    )
    await feed.http.aclose()
    assert result.attempts[0].status is CollectionStatus.EMPTY
