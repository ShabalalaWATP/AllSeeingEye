"""Offline regional RSS onboarding checks. Fixtures contain synthetic text only."""

from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

import pytest

from ase.adapters.feeds.http import FeedFetchError
from ase.adapters.feeds.rss import MAX_ITEMS, RssConnector, RssOptions
from ase.adapters.feeds.rss_seeds import RssSeed
from ase.adapters.feeds.rss_seeds_regional import REGIONAL_SEEDS
from ase.adapters.feeds.rss_sources import RSS_SEEDS
from ase.domain.events import Credibility, GeoConfidence, Reliability
from feeds_helpers import FIXTURES, NOW, FakeClock, FakeHttp, make_spec


@pytest.mark.parametrize("seed", REGIONAL_SEEDS, ids=lambda seed: seed.spec.id)
async def test_regional_feeds_preserve_metadata_without_article_text(seed: RssSeed) -> None:
    payload = (FIXTURES / "regional_multilingual.xml").read_text("utf-8")
    http = FakeHttp({seed.spec.url: payload})
    events = await RssConnector(http, FakeClock(NOW), seed.spec, seed.options).fetch()  # type: ignore[arg-type]
    assert len(events) == 3
    assert {event.title for event in events} == {
        "Проверка источника",
        "来源核实",
        "بررسی منبع در ایران",
    }
    for event in events:
        assert event.source_id == seed.spec.id and event.language == seed.spec.language
        assert event.summary is None
        assert event.url and event.url.startswith("https://publisher.test/")
        assert event.geo_confidence is GeoConfidence.NONE and event.point is None
        assert event.reliability is Reliability.F
        assert event.credibility is Credibility.CANNOT_BE_JUDGED
        assert "official" not in event.tags
        assert event.published_at.tzinfo is UTC
    assert seed.spec.rating and seed.spec.rating.status == "unassessed"


def test_editions_share_origin_and_feedburner_is_not_publisher() -> None:
    seeds = {seed.spec.id: seed for seed in RSS_SEEDS}
    for first, second in [
        ("meduza_en", "meduza_ru"),
        ("hrana_en", "hrana_fa"),
        ("iranwire_en", "iranwire_fa"),
    ]:
        assert seeds[first].spec.independence_key == seeds[second].spec.independence_key
    assert seeds["cdt_zh"].spec.organisation == "China Digital Times"
    assert "aggregator" in seeds["cdt_zh"].spec.flags
    assert "ngo_reporting" in seeds["hrana_fa"].spec.flags
    assert {seed.spec.id for seed in REGIONAL_SEEDS} <= seeds.keys()


async def test_oldest_first_feed_selects_newest_with_bounded_output_and_truncation() -> None:
    count = MAX_ITEMS + 50
    start = datetime(2026, 8, 1, tzinfo=UTC)
    items = "".join(
        f"<item><guid>{i}</guid><title>Record {i}</title>"
        f"<pubDate>{format_datetime(start + timedelta(hours=i))}</pubDate></item>"
        for i in range(count)
    )
    http = FakeHttp({"feeds.test": f"<rss><channel>{items}</channel></rss>"})
    events = await RssConnector(
        http, FakeClock(NOW), make_spec(), RssOptions(newest_first=True)
    ).fetch()  # type: ignore[arg-type]
    assert len(events) == MAX_ITEMS
    assert events[0].title == f"Record {count - 1}"
    assert events[-1].title == "Record 50"
    assert events[0].attributes["feed_items_available"] == count
    assert events[0].attributes["feed_items_limit"] == MAX_ITEMS
    assert events[0].attributes["feed_items_truncated"] is True


@pytest.mark.parametrize(
    "payload",
    [
        "<html><body>Blocked</body></html>",
        "<html><item><title>Fake</title><guid>x</guid></item></html>",
        "<error>Not available</error>",
    ],
)
async def test_well_formed_html_and_error_xml_are_not_empty_success(payload: str) -> None:
    with pytest.raises(FeedFetchError, match="not an RSS or Atom"):
        await RssConnector(FakeHttp({"feeds.test": payload}), FakeClock(NOW), make_spec()).fetch()  # type: ignore[arg-type]


async def test_empty_valid_feed_and_stable_duplicate_identity() -> None:
    empty = RssConnector(
        FakeHttp({"feeds.test": "<rss><channel /></rss>"}), FakeClock(NOW), make_spec()
    )  # type: ignore[arg-type]
    assert await empty.fetch() == []
    payload = (
        "<rss><channel><item><guid>x</guid><title>Unchanged</title>"
        "<pubDate>Sun, 06 Sep 2026 12:00:00 GMT</pubDate></item></channel></rss>"
    )
    connector = RssConnector(FakeHttp({"feeds.test": payload}), FakeClock(NOW), make_spec())  # type: ignore[arg-type]
    first, second = await connector.fetch(), await connector.fetch()
    assert first[0].id == second[0].id and first[0].content_hash == second[0].content_hash
