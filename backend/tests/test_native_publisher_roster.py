"""Native feed safety contracts and translation policy, with synthetic fixture headlines."""

import json
from dataclasses import asdict, replace
from datetime import datetime
from pathlib import Path

import httpx
import pytest

from ase.adapters.bus.memory import InMemoryEventBus
from ase.adapters.feeds import rss_seeds
from ase.adapters.feeds.roster_probe import RosterProbe
from ase.adapters.feeds.rss_seeds import NATIVE_SEEDS
from ase.adapters.packaged_json import CatalogueError
from ase.adapters.research.regional import RegionalFeedResearchProvider
from ase.adapters.store.memory import InMemoryEventStore
from ase.application.translate.queue import (
    BATCH,
    CALLS_PER_HOUR,
    TranslationQueue,
    needs_translation,
)
from ase.container.research_native_allocation_profiles import native_allocation_profiles
from feeds_helpers import NOW, FakeClock, make_event
from research_feed_helpers import QUERY

PAYLOAD = (
    "<rss><channel><item><guid>a</guid><title>Native headline</title>"
    "<link>https://example.test/article</link><description>Secret body text</description>"
    "<pubDate>Sun, 06 Sep 2026 12:00:00 GMT</pubDate></item></channel></rss>"
)


def test_roster_has_live_evidence_languages_ratings_and_shared_ownership():
    assert len(NATIVE_SEEDS) == 15
    assert {s.spec.language for s in NATIVE_SEEDS} == {
        "ar",
        "tr",
        "he",
        "hi",
        "ur",
        "ja",
        "ko",
        "de",
        "fr",
        "ha",
        "sw",
    }
    assert {s.spec.organisation for s in NATIVE_SEEDS if s.spec.id.startswith("bbc_")} == {"BBC"}
    profiles = native_allocation_profiles()
    evidence = json.loads(
        (
            Path(__file__).parents[2] / "docs/evidence/native_publisher_probes_2026_09_30.json"
        ).read_text("utf-8")
    )
    rows = {row["source_id"]: row for row in evidence["probes"]}
    for seed in NATIVE_SEEDS:
        row = rows[seed.spec.id]
        assert row["decision"] == "included"
        assert row["url"] == seed.spec.url
        assert row["http_status"] == 200 and row["item_count"] > 0
        assert row["discovery_url"].startswith("https://")
        assert datetime.fromisoformat(row["observed_at"]).tzinfo is not None
        assert datetime.fromisoformat(row["newest_publication"]).tzinfo is not None
        assert seed.spec.reliability.value == "F"
        assert seed.spec.rating.status == "unassessed"
        assert seed.options.headlines_only and seed.options.translate_on_demand
        assert seed.options.credibility.value == 6
        assert profiles[f"research_regional_{seed.spec.id}"].local_language


@pytest.mark.parametrize("value", ["true", 1, None])
def test_on_demand_option_is_a_strict_boolean(value):
    option = {
        "subtype": "article",
        "tags": [],
        "credibility": "cannot_be_judged",
        "rationale": "Fixture",
        "headlines_only": True,
        "newest_first": False,
        "translate_on_demand": value,
    }
    with pytest.raises(CatalogueError):
        rss_seeds._options("native", option)


async def test_probe_uses_parser_preserves_policy_and_saves_only_counts_and_dates():
    seed = replace(NATIVE_SEEDS[0], spec=replace(NATIVE_SEEDS[0].spec, url="https://8.8.8.8/rss"))
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, text=PAYLOAD)

    probe = RosterProbe(FakeClock(NOW), [seed], transport=httpx.MockTransport(handler))
    try:
        result, events = await probe.fetch(seed)
    finally:
        await probe.aclose()
    assert len(requests) == 1
    assert result.http_status == 200 and result.item_count == 1 and result.newest_publication
    assert events[0].summary is None and events[0].language == seed.spec.language
    assert events[0].grade == "F6" and not needs_translation(events[0])
    saved = json.dumps(asdict(result), default=str)
    assert "Native headline" not in saved and "Secret body" not in saved
    assert "example.test/article" not in saved


@pytest.mark.parametrize(
    ("status", "body", "error"),
    [(403, "private body", True), (200, "<html />", True), (200, "<rss />", False)],
)
async def test_probe_retains_refusal_or_empty_status_without_upstream_text(status, body, error):
    seed = replace(NATIVE_SEEDS[0], spec=replace(NATIVE_SEEDS[0].spec, url="https://8.8.4.4/rss"))
    probe = RosterProbe(
        FakeClock(NOW),
        [seed],
        transport=httpx.MockTransport(lambda _: httpx.Response(status, text=body)),
    )
    try:
        result, events = await probe.fetch(seed)
    finally:
        await probe.aclose()
    assert result.http_status == status and bool(result.error) is error
    assert events == [] and result.newest_publication is None
    assert "private body" not in json.dumps(asdict(result), default=str)


async def test_probe_keeps_ssrf_guard_before_transport():
    seed = replace(NATIVE_SEEDS[0], spec=replace(NATIVE_SEEDS[0].spec, url="https://127.0.0.1/rss"))
    calls = []
    probe = RosterProbe(FakeClock(NOW), [seed], transport=httpx.MockTransport(calls.append))
    try:
        result, _ = await probe.fetch(seed)
    finally:
        await probe.aclose()
    assert calls == [] and result.error == "FeedFetchError" and result.http_status is None


async def test_on_demand_title_does_not_consume_budget_or_cached_automatic_translation():
    class Translator:
        def __init__(self):
            self.calls = 0

        async def translate(self, items):
            self.calls += 1
            return ["English title" for _ in items]

    store = InMemoryEventStore()
    automatic = replace(make_event("auto", title="Same"), language="fr")
    on_demand = replace(automatic, id="manual", tags=frozenset({"translate_on_demand"}))
    store.upsert([automatic, on_demand])
    translator = Translator()
    queue = TranslationQueue(store, InMemoryEventBus(), translator, FakeClock(NOW))
    assert await queue.run_once() == 1
    assert await queue.run_once() == 0
    assert translator.calls == queue.calls_this_hour == 1
    assert store.get("manual").title_en is None
    assert store.get(automatic.id).title_en == "English title"
    assert BATCH == 20 and CALLS_PER_HOUR == 60


def test_native_editorial_coverage_can_route_multiple_countries_without_geolocation():
    seed = next(s for s in NATIVE_SEEDS if s.spec.id == "bbc_swahili")
    provider = RegionalFeedResearchProvider(None, FakeClock(NOW), seed)
    query = replace(QUERY, languages=("sw",), country_iso="TZ")
    assert provider.supports(query)
    assert provider.supports(replace(query, country_iso="KE", country_isos=()))
    assert not provider.supports(replace(query, country_iso="DE", country_isos=()))
    assert provider.supports(
        replace(query, country_iso="DE", country_isos=(), source_ids=(provider.id,))
    )
