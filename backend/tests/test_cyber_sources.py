"""Cyber sources retain publisher claims, measured signals and explicit uncertainty."""

from datetime import UTC, datetime, timedelta

import httpx
import pytest

from ase.adapters.feeds.cisa_kev import CisaKevConnector
from ase.adapters.feeds.cyber import IodaConnector, RansomwareConnector
from ase.adapters.feeds.cyber_rss import CyberRssConnector
from ase.adapters.feeds.http import FeedFetchError
from ase.adapters.feeds.registry import build_connectors
from ase.adapters.feeds.rss_seeds_cyber import CYBER_SEEDS
from ase.adapters.research.publisher import PublisherFeedResearchProvider
from ase.container.research_feeds import public_research_feeds
from ase.container.research_sources import research_source_specs
from ase.domain.events import Category, GeoConfidence
from feeds_helpers import NOW, FakeHttp, load_fixture
from helpers import FakeClock
from research_feed_helpers import CLOCK, QUERY, PublicFeed, item, rss


@pytest.mark.parametrize("seed", CYBER_SEEDS)
async def test_cyber_publishers_share_guarded_pipeline_without_implied_geography(
    monkeypatch: pytest.MonkeyPatch,
    seed,
) -> None:
    payload = rss(item(extra="<point>51.5 -0.1</point><category>GB</category>"))
    feed = PublicFeed(monkeypatch, httpx.Response(200, text=payload))
    connector = CyberRssConnector(feed.http, CLOCK, seed.spec, seed.options)
    try:
        events = await connector.fetch()
        batch = await PublisherFeedResearchProvider(feed.http, CLOCK, seed).collect(QUERY)
    finally:
        await feed.http.aclose()
    live, private = events[0], batch.items[0]
    assert live.id == private.id
    assert live.category is Category.CYBER
    assert live.subtype in {"advisory", "threat_report"}
    for event in (live, private):
        assert event.grade == "F6" and event.summary is None
        assert event.point is None and event.country_iso is None
        assert event.geo_confidence is GeoConfidence.NONE
        assert event.attributes["original_source_id"] == seed.spec.id
        assert event.attributes["original_source_name"] == seed.spec.name
        assert event.attributes["original_source_organisation"] == seed.spec.organisation
        assert "unknown" in event.attributes["geography_basis"]
    assert len(feed.requests) == len(feed.guarded) == 2
    assert all(str(request.url) == seed.spec.url for request in feed.requests)


async def test_cyber_rss_missing_dates_remain_unknown_and_private_collection_excludes_them(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seed = CYBER_SEEDS[0]
    feed = PublicFeed(monkeypatch, httpx.Response(200, text=rss(item(date=""))))
    try:
        events = await CyberRssConnector(feed.http, CLOCK, seed.spec, seed.options).fetch()
        batch = await PublisherFeedResearchProvider(feed.http, CLOCK, seed).collect(QUERY)
    finally:
        await feed.http.aclose()
    assert len(events) == 1 and events[0].published_at is None
    assert not batch.items


def test_live_and_research_registry_preserve_original_publisher_control_and_independence() -> None:
    http = FakeHttp()
    ids = {seed.spec.id for seed in CYBER_SEEDS}
    connectors = build_connectors(http, CLOCK)  # type: ignore[arg-type]
    assert ids <= {connector.spec.id for connector in connectors}
    assert all(
        isinstance(connector, CyberRssConnector)
        for connector in connectors
        if connector.spec.id in ids
    )
    assert not ids & {
        connector.spec.id for connector in build_connectors(http, CLOCK, disabled=ids)
    }
    specs = {spec.id: spec for spec in research_source_specs()}
    for seed in CYBER_SEEDS:
        derived = f"research_publisher_{seed.spec.id}"
        assert specs[derived].independence_key == seed.spec.independence_key
        assert derived not in {spec.id for spec in research_source_specs((seed.spec.id,))}
    providers = public_research_feeds(http, CLOCK, spatial=False)  # type: ignore[arg-type]
    assert {f"research_publisher_{key}" for key in ids} <= {p.id for p in providers}
    spatial = public_research_feeds(http, CLOCK, spatial=True)  # type: ignore[arg-type]
    assert not any(p.id.startswith("research_publisher_cyber_") for p in spatial)


@pytest.mark.parametrize(
    "url",
    [
        "http://criminal.onion/leak",
        "https://criminal.example/leak",
        "https://www.ransomware.live.evil.example/id/test",
        "https://user@www.ransomware.live/id/test",
        "https://www.ransomware.live:444/id/test",
        "https://[invalid",
        "https://www.ransomware.live/id/../../leak",
    ],
)
async def test_claims_never_expose_criminal_links_or_fabricate_missing_dates(url: str) -> None:
    payload = {
        "victim": "Example",
        "group": "example",
        "url": url,
        "claim_url": "http://criminal.onion/leak",
        "discovered": "invalid",
    }
    connector = RansomwareConnector(FakeHttp({"recentvictims": [payload]}), FakeClock(NOW))
    event = (await connector.fetch())[0]
    assert event.url == "https://www.ransomware.live/"
    assert event.published_at is None and event.observed_at == NOW
    assert "claim_url" not in event.attributes
    assert "criminal.onion" not in repr(event)


async def test_valid_aggregator_reference_drops_query_and_fragment() -> None:
    payload = {
        "victim": "Example",
        "group": "example",
        "url": "https://www.ransomware.live/id/RXhhbXBsZQ==?private=1#fragment",
    }
    event = (
        await RansomwareConnector(FakeHttp({"recentvictims": [payload]}), FakeClock(NOW)).fetch()
    )[0]
    assert event.url == "https://www.ransomware.live/id/RXhhbXBsZQ=="


@pytest.mark.parametrize("stamp", [None, "invalid", float("nan"), float("inf"), 1e99, True])
async def test_outage_missing_or_invalid_measurement_dates_are_unknown(stamp) -> None:
    alert = {"entity": {"type": "country", "code": "GB"}, "level": "critical", "time": stamp}
    event = (await IodaConnector(FakeHttp({"outages/alerts": {"data": [alert]}}), CLOCK).fetch())[0]
    assert event.published_at is None
    assert "not evidence of a cyberattack" in event.attributes["attribution_status"]


async def test_malformed_entities_are_skipped_and_outage_rows_are_bounded() -> None:
    alert = {"entity": {"type": "country", "code": "GB"}, "level": "critical", "time": 1000}
    alerts = [
        {**alert, "entity": "invalid"},
        {**alert, "entity": {"type": "country", "code": "../"}},
    ]
    alerts.extend([alert] * 350)
    events = await IodaConnector(FakeHttp({"outages/alerts": {"data": alerts}}), CLOCK).fetch()
    assert len(events) == 298


@pytest.mark.parametrize(
    "connector,payload",
    [
        (RansomwareConnector, {"error": "unavailable"}),
        (IodaConnector, {"data": None}),
        (IodaConnector, {"data": [], "error": "unavailable"}),
        (CisaKevConnector, {"vulnerabilities": None}),
    ],
)
async def test_upstream_schema_failure_is_health_error_not_empty_activity(
    connector, payload
) -> None:
    class ResponseHttp:
        async def get_json(self, *args, **kwargs):
            return payload

    with pytest.raises(FeedFetchError):
        await connector(ResponseHttp(), CLOCK).fetch()


async def test_kev_skips_nonrecords_and_future_catalogue_dates() -> None:
    record = load_fixture("cisa_kev.json")["vulnerabilities"][0]
    future = {**record, "dateAdded": (NOW + timedelta(days=1)).date().isoformat()}
    current = {**record, "dateAdded": NOW.date().isoformat()}
    events = await CisaKevConnector(
        FakeHttp({"cisa.gov": {"vulnerabilities": [None, [], future, current]}}), FakeClock(NOW)
    ).fetch()
    assert len(events) == 1 and events[0].published_at == NOW


@pytest.mark.parametrize("zone,hour", [("CEST", 12), ("CET", 13)])
async def test_cert_eu_declared_timezone_is_converted_with_raw_date_preserved(
    monkeypatch: pytest.MonkeyPatch,
    zone: str,
    hour: int,
) -> None:
    raw = f"Sat, 05 Sep 2026 14:00:00 {zone}"
    seed = next(seed for seed in CYBER_SEEDS if seed.spec.id == "cyber_cert_eu")
    feed = PublicFeed(monkeypatch, httpx.Response(200, text=rss(item(date=raw))))
    try:
        live = (await CyberRssConnector(feed.http, CLOCK, seed.spec, seed.options).fetch())[0]
        private = (
            await PublisherFeedResearchProvider(feed.http, CLOCK, seed).collect(QUERY)
        ).items[0]
    finally:
        await feed.http.aclose()
    for event in (live, private):
        assert event.published_at == datetime(2026, 9, 5, hour, tzinfo=UTC)
        assert event.source_dates[0].raw_text == raw
        assert event.source_dates[0].method == "ase-cert-eu-pubdate-zone-v1"


async def test_unknown_timezone_and_other_publishers_do_not_inherit_cert_eu_conversion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seed = CYBER_SEEDS[0]
    feed = PublicFeed(
        monkeypatch, httpx.Response(200, text=rss(item(date="Sat, 05 Sep 2026 14:00:00 CEST")))
    )
    try:
        event = (await CyberRssConnector(feed.http, CLOCK, seed.spec, seed.options).fetch())[0]
    finally:
        await feed.http.aclose()
    assert event.published_at is None
