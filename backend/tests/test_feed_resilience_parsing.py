"""KAN-200: one malformed upstream value costs one item, never the whole poll."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest

from ase.adapters.bus.memory import InMemoryEventBus
from ase.adapters.feeds import (
    bluesky_posts,
    eonet,
    humanitarian,
    mastodon,
    nws,
    satellites,
    space,
    telegram_preview,
    youtube,
)
from ase.adapters.feeds.rss import RssConnector
from ase.adapters.feeds.timestamps import parse_utc
from ase.adapters.store.memory import InMemoryEventStore
from ase.application.feeds import pipeline as pipeline_module
from ase.application.feeds.health import HealthRegistry
from ase.application.feeds.pipeline import Normaliser, Pipeline, safe_url
from ase.application.feeds.scheduler import FeedScheduler
from feeds_helpers import NOW, FakeClock, FakeConnector, FakeHttp, make_event, make_spec

EARLIEST_EAST = "0001-01-01T00:00:00+05:00"
LATEST_WEST = "9999-12-31T23:59:59-05:00"


@pytest.mark.parametrize(
    "value",
    [
        "http://[bad",
        "http://[abc]/",
        f"https://exa{chr(0xFF0F)}mple.com/story",  # NFKC turns the fullwidth solidus into "/"
        "https://bbc.co.uk@evil.example/x",
        "https://user:secret@example.com/",
        "https://example.com/a\nb",
        "https://example.com/\x00",
        "http://example.com:99999/",
        "http://example.com:port/",
        "javascript:alert(1)",
        "https:///no-host",
    ],
)
def test_unsafe_or_malformed_links_become_none(value: str) -> None:
    assert safe_url(value) is None


@pytest.mark.parametrize(
    "value",
    ["https://example.com/a?b=c#d", " http://example.com:8080/x ", "https://[2001:db8::1]/"],
)
def test_ordinary_links_survive(value: str) -> None:
    assert safe_url(value) == value.strip()


def test_normaliser_keeps_the_batch_when_one_link_is_malformed() -> None:
    good = make_event("good")
    bad = make_event("bad").with_changes(url="http://[bad")
    later = make_event("later")
    result = Normaliser().process([good, bad, later])
    assert [event.id for event in result] == [good.id, bad.id, later.id]
    assert result[1].url is None


def test_normaliser_drops_only_the_offending_event(monkeypatch: pytest.MonkeyPatch) -> None:
    original = pipeline_module.safe_url

    def exploding(value: str | None) -> str | None:
        if value and value.endswith("/boom"):
            raise ValueError("malformed")
        return original(value)

    monkeypatch.setattr(pipeline_module, "safe_url", exploding)
    events = [make_event("one"), make_event("boom"), make_event("two")]
    result = Normaliser().process(events)
    assert [event.id for event in result] == [events[0].id, events[2].id]


async def test_a_malformed_link_does_not_abort_the_poll() -> None:
    store = InMemoryEventStore()
    events = [make_event("ok"), make_event("bad").with_changes(url="http://[abc]/")]
    scheduler = FeedScheduler(
        [FakeConnector(make_spec(), events)],
        Pipeline([Normaliser()]),
        store,
        InMemoryEventBus(),
        HealthRegistry(),
        FakeClock(NOW),
    )
    outcome = await scheduler.poll_once(scheduler.connectors[0])
    assert outcome.ok and outcome.fetched == 2
    assert store.get(events[1].id) is not None
    assert store.get(events[1].id).url is None  # type: ignore[union-attr]


@pytest.mark.parametrize("value", [EARLIEST_EAST, LATEST_WEST, "not a date", "", None, 7])
def test_shared_parser_rejects_unusable_values(value: object) -> None:
    assert parse_utc(value) is None


def test_shared_parser_normalises_to_utc() -> None:
    assert parse_utc("2026-09-05T02:00:00+02:00") == NOW
    assert parse_utc("2026-09-05T00:00:00Z") == NOW
    assert parse_utc("2026-09-05T00:00:00") == NOW
    assert parse_utc("2026-09-05T00:00:00Z" + " " * 60) is None


FALLBACK_PARSERS: list[Callable[[object, datetime], datetime]] = [
    mastodon._when,
    nws._when,
    space._when,
    humanitarian._when,
    youtube.parsed_time,
    bluesky_posts.created_at,
]


@pytest.mark.parametrize("parse", FALLBACK_PARSERS)
@pytest.mark.parametrize("value", [EARLIEST_EAST, LATEST_WEST])
def test_extreme_timestamps_fall_back_instead_of_raising(
    parse: Callable[[object, datetime], datetime], value: str
) -> None:
    assert parse(value, NOW) == NOW


@pytest.mark.parametrize(
    "parse", [telegram_preview._timestamp, eonet._parse_date, satellites.orbital_epoch]
)
@pytest.mark.parametrize("value", [EARLIEST_EAST, LATEST_WEST])
def test_extreme_timestamps_are_dropped_instead_of_raising(
    parse: Callable[[str], datetime | None], value: str
) -> None:
    assert parse(value) is None


def test_bluesky_still_clamps_future_posts_to_the_clock() -> None:
    assert bluesky_posts.created_at("2030-01-01T00:00:00Z", NOW) == NOW
    assert bluesky_posts.created_at("2026-09-04T00:00:00Z", NOW) == NOW - timedelta(days=1)


def _rss(*dates: str) -> str:
    items = "".join(
        f"<item><title>Item {n}</title><link>https://example.org/{n}</link>"
        f"<pubDate>{value}</pubDate></item>"
        for n, value in enumerate(dates)
    )
    return (
        f'<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>{items}</channel></rss>'
    )


async def test_rss_clamps_far_future_publication_dates_with_a_stable_hash() -> None:
    feed = _rss(
        "Mon, 01 Jan 2120 00:00:00 GMT",  # a century ahead: clamped to the clock
        "Sat, 05 Sep 2026 12:00:00 GMT",  # half a day ahead: publisher drift, kept
        "Fri, 04 Sep 2026 12:00:00 GMT",
    )
    clock = FakeClock(NOW)
    rss = RssConnector(FakeHttp({"feeds.test": feed}), clock, make_spec("feed_test"))  # type: ignore[arg-type]
    far, near, past = await rss.fetch()
    assert far.published_at == NOW
    assert near.published_at == datetime(2026, 9, 5, 12, tzinfo=UTC)
    assert past.published_at == datetime(2026, 9, 4, 12, tzinfo=UTC)
    clock.advance(timedelta(hours=1))
    again = (await rss.fetch())[0]
    # The clamp moves with the clock, but the item is not treated as changed content.
    assert again.published_at == NOW + timedelta(hours=1)
    assert again.content_hash == far.content_hash
