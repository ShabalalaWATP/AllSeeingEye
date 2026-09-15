"""Expanded news coverage keeps source identity, rights, geography and hard limits honest."""

import httpx
import pytest

from ase.adapters.feeds.news_rss import NewsRssConnector
from ase.adapters.feeds.registry import build_connectors
from ase.adapters.feeds.rss_seeds_gap_news import GAP_NEWS_SEEDS
from ase.adapters.feeds.rss_seeds_news import NEWS_SEEDS
from ase.adapters.feeds.rss_seeds_uk_news import UK_NEWS_SEEDS
from ase.adapters.feeds.rss_seeds_world_news import WORLD_NEWS_SEEDS
from ase.adapters.feeds.rss_sources import RSS_SEEDS
from ase.adapters.research.publisher import PUBLISHER_SEEDS
from ase.application.feeds.grading import profiles_from_specs
from ase.application.feeds.pipeline import Normaliser
from ase.domain.events import Category, GeoConfidence, Reliability
from feeds_helpers import FakeHttp
from research_feed_helpers import CLOCK, PublicFeed, item, rss


@pytest.mark.parametrize("seed", NEWS_SEEDS, ids=lambda seed: seed.spec.id)
async def test_new_feed_is_one_guarded_headline_request_with_original_publisher(
    monkeypatch: pytest.MonkeyPatch,
    seed,
) -> None:
    body = rss(item(extra="<point>51.5 -0.1</point><source>Declared wire</source>"))
    feed = PublicFeed(monkeypatch, httpx.Response(200, text=body))
    try:
        connectors = build_connectors(feed.http, CLOCK)
        connector = next(row for row in connectors if row.spec.id == seed.spec.id)
        assert isinstance(connector, NewsRssConnector)
        events = Normaliser().process(await connector.fetch())
    finally:
        await feed.http.aclose()
    assert len(events) == len(feed.requests) == len(feed.guarded) == 1
    assert str(feed.requests[0].url) == seed.spec.url
    event = events[0]
    assert event.source_id == seed.spec.id and event.category is Category.NEWS
    assert event.grade == "F6" and event.summary is None
    assert event.language == seed.spec.language
    assert event.point is None and event.country_iso is None
    assert event.geo_confidence is GeoConfidence.NONE
    assert event.attributes["original_source_name"] == seed.spec.name
    assert event.attributes["original_source_organisation"] == seed.spec.organisation
    assert event.attributes["declared_upstream_publisher"] == "Declared wire"
    assert "no fresh private" in event.attributes["research_scope"]
    assert event.url == "https://publisher.example/1"


def test_news_seed_catalogue_is_distinct_bounded_and_explicitly_unassessed() -> None:
    assert len(UK_NEWS_SEEDS) == 14 and len(WORLD_NEWS_SEEDS) == 24
    assert len(GAP_NEWS_SEEDS) == 15
    assert len(NEWS_SEEDS) == 53
    ids = {seed.spec.id for seed in NEWS_SEEDS}
    assert len(ids) == len(NEWS_SEEDS)
    assert len({seed.spec.url for seed in NEWS_SEEDS}) == len(NEWS_SEEDS)
    assert ids <= {seed.spec.id for seed in RSS_SEEDS}
    assert not ids & {seed.spec.id for seed in PUBLISHER_SEEDS}
    for seed in NEWS_SEEDS:
        assert seed.spec.url.startswith("https://") and not seed.spec.requires_key
        assert seed.spec.poll_interval.total_seconds() == 1800
        assert seed.spec.reliability is Reliability.F
        assert seed.options.headlines_only and seed.options.newest_first
        assert seed.options.country_category_domain is None
        assert seed.spec.licence_note and "retained_feed_research" in seed.spec.flags
        rating = seed.spec.rating
        assert rating is not None and rating.status == "unassessed"
        assert rating.assessed_grade is None and not rating.publisher_reliability_assessed
        assert seed.spec.name in rating.basis and "geography" in rating.scope
        assert rating.provenance_role == "publisher" and rating.reviewed_at is None


def test_shared_publishers_do_not_become_independent_sources() -> None:
    profiles = profiles_from_specs(seed.spec for seed in RSS_SEEDS)
    families = (
        (
            "bbc_world",
            "news_bbc_uk",
            "news_bbc_scotland",
            "news_bbc_wales",
            "news_bbc_northern_ireland",
        ),
        ("guardian_world", "news_guardian_uk"),
        (
            "news_wales_online",
            "news_belfast_live",
            "news_manchester_evening",
            "news_birmingham_live",
        ),
        ("news_herald_scotland", "news_northern_echo"),
        ("france24_en", "news_france24_ar", "news_rfi_en", "news_rfi_fr"),
        ("news_euronews", "news_africanews"),
    )
    for family in families:
        assert len({profiles[source_id].independence_key for source_id in family}) == 1


def test_disabling_new_feeds_removes_their_connectors_without_private_inventory_growth() -> None:
    ids = {seed.spec.id for seed in NEWS_SEEDS}
    connectors = build_connectors(FakeHttp(), CLOCK, disabled=ids)
    assert not ids & {connector.spec.id for connector in connectors}
    assert len(PUBLISHER_SEEDS) == 55


async def test_missing_dates_are_unknown_and_feed_item_cap_and_dedup_still_apply(
    monkeypatch,
) -> None:
    seed = NEWS_SEEDS[0]
    feed = PublicFeed(monkeypatch, httpx.Response(200, text=rss(item(date=""))))
    try:
        event = (await NewsRssConnector(feed.http, CLOCK, seed.spec, seed.options).fetch())[0]
    finally:
        await feed.http.aclose()
    assert event.published_at is None
    body = rss("".join(item(str(i // 2)) for i in range(250)))
    feed = PublicFeed(monkeypatch, httpx.Response(200, text=body))
    try:
        raw = await NewsRssConnector(feed.http, CLOCK, seed.spec, seed.options).fetch()
    finally:
        await feed.http.aclose()
    assert len(raw) == 200
    events = Normaliser().process(raw)
    assert len(events) == 100
    assert all(event.attributes["feed_items_available"] == 250 for event in events)
    assert all(event.attributes["feed_items_truncated"] for event in events)


def test_explicit_personal_use_rights_are_not_replaced_with_generic_reuse_claim() -> None:
    rows = {seed.spec.id: seed for seed in NEWS_SEEDS}
    for source_id in ("news_independent_uk", "news_cna_asia"):
        assert "personal, non-commercial" in rows[source_id].spec.licence_note
