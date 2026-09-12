"""Economic-only selection, honest regional attribution and current source controls."""

from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from ase.adapters.feeds.rss import RssConnector
from ase.adapters.feeds.rss_seeds_economy import ECONOMY_SEEDS
from ase.adapters.feeds.rss_seeds_outlets import OUTLET_SEEDS
from ase.adapters.store.memory import InMemoryEventStore
from ase.application.economy_news import EconomyNewsService
from ase.container.research_feed_specs import additional_feed_specs
from ase.domain.economy_news import ECONOMIC_NEWS_IDS, economic_regions, economic_viewpoint
from ase.domain.events import Category
from ase.domain.source_discovery import source_coverage
from feeds_helpers import NOW, FakeClock, FakeHttp, make_event

SEEDS = {row.spec.id: row for row in ECONOMY_SEEDS}


def news(key="one", **changes):
    value = make_event(
        key,
        source_id="economic_bbc_business",
        category=Category.ECONOMIC,
        title="Global inflation report",
        point=None,
        published_at=NOW - timedelta(minutes=1),
    )
    return replace(value, **changes)


def service(events=(), disabled=()):
    store = InMemoryEventStore()
    store.upsert(events)
    admission = SimpleNamespace(
        enabled_many=AsyncMock(
            side_effect=lambda ids: {key: key not in disabled for key in ids},
        )
    )
    return EconomyNewsService(
        store,
        FakeClock(NOW),
        {key: seed.spec for key, seed in SEEDS.items()},
        admission,
    ), admission


async def test_only_reviewed_economic_publishers_and_valid_dates_are_news():
    current = news()
    unrelated = news("conflict", category=Category.CONFLICT, title="A battle was reported")
    unreviewed = news("random", source_id="random-economic", title="Economy rumour")
    stale = news("old", published_at=NOW - timedelta(hours=73), title="Old inflation report")
    future = news("future", published_at=NOW + timedelta(seconds=1), title="Future report")
    undated = news("undated", published_at=None, title="Unknown date")
    svc, _ = service((current, unrelated, unreviewed, stale, future, undated))
    result = await svc.read()
    assert [row.id for row in result.items] == [current.id]
    assert result.items[0].region_codes == ()
    assert result.window_hours == 48 and result.as_of == NOW


async def test_headline_subject_and_feed_remit_do_not_invent_event_location():
    russian = news("ru", title="Russian inflation rises")
    china_feed = news("cn", source_id="economic_scmp_china", title="Exports increased")
    # A shared source's UK identity alone must not tag a global item as British.
    svc, _ = service((news(), russian, china_feed))
    assert [row.id for row in (await svc.read("CN")).items] == [china_feed.id]
    assert [row.id for row in (await svc.read("RU")).items] == [russian.id]
    assert not (await svc.read("GB")).items
    assert russian.point is None and russian.country_iso is None
    assert economic_regions(news(title="How inflation affects us")) == ()
    assert economic_regions(news(title="US inflation falls")) == ("US",)


async def test_enabled_sources_checked_before_read_and_before_release():
    svc, admission = service((news(),), disabled=("economic_bbc_business",))
    assert not (await svc.read()).items
    svc, admission = service((news(),))
    admission.enabled_many.side_effect = [dict.fromkeys(ECONOMIC_NEWS_IDS, True), {}]
    assert not (await svc.read()).items
    assert admission.enabled_many.await_count == 2
    svc, _ = service((news(),), disabled=ECONOMIC_NEWS_IDS)
    assert not (await svc.read()).items


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "https://name:secret@example.com",
        "https://:secret@example.com",
        "https://[",
        None,
    ],
)
async def test_unsafe_links_are_never_released(url):
    svc, _ = service((news(url=url),))
    assert not (await svc.read()).items


async def test_result_cap_and_duplicate_titles_are_bounded():
    rows = [news(str(n), title=f"Inflation report {n}") for n in range(120)]
    svc, _ = service((*rows, news("copy", title=rows[0].title)))
    result = await svc.read(limit=100)
    assert len(result.items) == 100
    assert len({row.title for row in result.items}) == 100
    with pytest.raises(ValueError):
        await svc.read(limit=101)
    with pytest.raises(ValueError):
        await svc.read("ZZ")


@pytest.mark.parametrize("seed", ECONOMY_SEEDS, ids=lambda seed: seed.spec.id)
async def test_economic_connectors_discard_bodies_keep_viewpoint_and_unassessed_grade(seed):
    xml = """<rss><channel><item><title>Inflation outlook</title>
      <link>https://publisher.example/inflation</link>
      <pubDate>Fri, 04 Sep 2026 22:00:00 GMT</pubDate>
      <description>Private article body must not be retained</description>
      </item></channel></rss>"""
    http = FakeHttp({seed.spec.url: xml})
    rows = await RssConnector(http, FakeClock(NOW), seed.spec, seed.options).fetch()
    assert len(rows) == 1 and http.requests == [seed.spec.url]
    row = rows[0]
    assert row.category is Category.ECONOMIC and row.grade == "F6" and row.summary is None
    assert row.point is None and row.country_iso is None
    if seed.spec.id in {"economic_cgtn_business", "economic_tehran_times"}:
        assert economic_viewpoint(row) == "state_aligned"
    elif "official_issuer" in seed.options.tags:
        assert economic_viewpoint(row) == "official_issuer"
    else:
        assert economic_viewpoint(row) == "publisher"


def test_registered_ids_match_reviewed_topics_and_economy_not_politics_url():
    assert set(SEEDS) == set(ECONOMIC_NEWS_IDS)
    assert SEEDS["economic_tehran_times"].spec.url.endswith("/697")
    existing = {seed.spec.id: seed.spec for seed in OUTLET_SEEDS}
    for topic, general in (
        ("economic_bbc_business", "bbc_world"),
        ("economic_guardian_business", "guardian_world"),
        ("economic_scmp_china", "scmp_news"),
    ):
        assert SEEDS[topic].spec.independence_key == existing[general].independence_key
    assert source_coverage("research_publisher_economic_scmp_china").countries == ("CN",)
    private = {spec.id: spec for spec in additional_feed_specs()}
    assert "state_aligned" in private["research_publisher_economic_cgtn_business"].flags
    assert "official_issuer" in private["research_publisher_economic_bank_russia"].flags
