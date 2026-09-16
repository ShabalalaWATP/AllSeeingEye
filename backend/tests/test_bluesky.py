"""Bluesky public author feeds: strict parsing, a reviewed registry and polite polling."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest

from ase.adapters.feeds.bluesky import (
    ACCOUNTS_PER_CYCLE,
    FILTER,
    POSTS_PER_ACCOUNT,
    SPEC,
    BlueskyConnector,
    author_feed_url,
)
from ase.adapters.feeds.bluesky_accounts import (
    ACCOUNTS,
    TOPICS,
    VIEWPOINTS,
    BlueskyAccount,
    load_accounts,
    valid_handle,
)
from ase.adapters.feeds.bluesky_posts import EXCERPT_CHARS, MIN_REPLY_CHARS, record_key, to_event
from ase.adapters.feeds.host_pacing import BLUESKY_HOST, DEFAULT_HOST_INTERVALS, HostPacer
from ase.adapters.feeds.http import FeedFetchError
from ase.adapters.feeds.registry import build_connectors
from ase.domain.events import Category, Credibility, Reliability
from ase.domain.social import platform_groups, top_hashtags
from feeds_helpers import FakeClock, FakeHttp, load_fixture

NOW = datetime(2026, 9, 5, 22, 30, tzinfo=UTC)
KYIV = next(account for account in ACCOUNTS if account.handle == "kyivindependent.com")
REQUIRED_TOPICS = (
    "ukraine_russia",
    "china_taiwan",
    "indo_pacific",
    "middle_east",
    "korea",
    "south_asia",
    "africa",
    "latin_america",
    "finance_markets",
    "cyber_threat_intel",
    "drones_uncrewed",
    "defence_analysis",
    "world_leaders",
    "maritime_aviation",
    "space",
    "energy",
    "humanitarian",
    "disinformation",
)


def connector(http: FakeHttp, per_cycle: int = ACCOUNTS_PER_CYCLE) -> BlueskyConnector:
    return BlueskyConnector(http, FakeClock(NOW), ACCOUNTS, per_cycle=per_cycle)  # type: ignore[arg-type]


def feed_http() -> FakeHttp:
    return FakeHttp({"actor=": load_fixture("bluesky_author_feed.json")})


async def test_author_feed_posts_become_graded_social_events() -> None:
    http = feed_http()
    events = await connector(http, per_cycle=1).fetch()
    assert http.requests == [
        "https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed"
        f"?actor=kyivindependent.com&limit={POSTS_PER_ACCOUNT}&filter={FILTER}"
    ]
    assert len(events) == 4
    first = events[0]
    assert first.source_id == SPEC.id and first.category is Category.SOCIAL
    assert first.subtype == "post" and first.geo_confidence.value == "none"
    assert first.reliability is Reliability.E
    assert first.credibility is Credibility.CANNOT_BE_JUDGED
    assert first.grade == "E6" and "unassessed" in first.grade_rationale
    assert first.url == "https://bsky.app/profile/kyivindependent.com/post/3lpostone"
    assert first.title.startswith("Air defence engaged drones over three oblasts overnight")
    assert len(first.title) <= 140
    assert first.summary is not None and len(first.summary) <= EXCERPT_CHARS
    assert first.language == "en"
    assert first.published_at == datetime(2026, 9, 5, 21, 40, 0, 123000, tzinfo=UTC)
    assert {"bluesky", "ukraine_russia"} <= first.tags
    assert first.attributes["account"] == "kyivindependent.com"
    assert first.attributes["display_name"] == "The Kyiv Independent"
    assert first.attributes["operator"] == KYIV.operator
    assert first.attributes["topic"] == "ukraine_russia"
    assert first.attributes["viewpoint"] == "publisher"
    assert first.attributes["media_attachments"] == 2
    assert first.attributes["likes"] == 30 and first.attributes["reposts"] == 12
    assert first.attributes["thread_reply"] is False
    assert not first.attributes["excerpt_truncated"]


async def test_reposts_short_replies_and_malformed_items_are_refused() -> None:
    events = await connector(feed_http(), per_cycle=1).fetch()
    keys = {str(event.url).rsplit("/", maxsplit=1)[-1] for event in events}
    assert {"3lpostone", "3lplongreply", "3lpfuture", "3lpbadtime"} == keys
    for refused in ("3lpreposted", "3lpshortreply", "3lpwrongauthor", "3lpnotapost", "3lpempty"):
        assert refused not in keys
    thread = next(event for event in events if str(event.url).endswith("3lplongreply"))
    assert thread.attributes["thread_reply"] is True
    assert thread.language == "uk" and len(thread.summary or "") >= MIN_REPLY_CHARS


async def test_author_supplied_times_and_languages_are_constrained() -> None:
    events = await connector(feed_http(), per_cycle=1).fetch()
    future = next(event for event in events if str(event.url).endswith("3lpfuture"))
    unparsable = next(event for event in events if str(event.url).endswith("3lpbadtime"))
    assert future.published_at == NOW and future.language == "und"
    assert unparsable.published_at == NOW and unparsable.language == "en-gb"


async def test_posts_group_on_the_social_board_by_account() -> None:
    events = await connector(feed_http(), per_cycle=1).fetch()
    groups = platform_groups(events)
    assert [(row.platform, row.instance, row.count) for row in groups] == [
        ("bluesky", "kyivindependent.com", 4)
    ]
    assert all(row.located == 0 for row in groups)
    # Registry topics are grouping metadata, not hashtags claimed by the author.
    assert not any(tag.tag == "ukraine_russia" for tag in top_hashtags(events))


def test_record_keys_and_handles_are_validated() -> None:
    assert record_key("at://did:plc:a/app.bsky.feed.post/3lpostone") == "3lpostone"
    assert record_key("at://did:plc:a/app.bsky.feed.like/3lpostone") is None
    assert record_key("https://bsky.app/profile/x/post/1") is None
    assert record_key("at://did:plc:a/app.bsky.feed.post/../../etc") is None
    assert record_key("at://did:plc:a/app.bsky.feed.post/" + "a" * 64) is None
    assert valid_handle("kyivindependent.com") and not valid_handle("no-dot")
    assert not valid_handle("bad handle.com") and not valid_handle("a..b.com")
    assert not valid_handle(".leading.com") and not valid_handle("x" * 80 + ".com")
    assert to_event("not-an-object", KYIV, SPEC, NOW) is None
    assert to_event({"post": {"record": {}}}, KYIV, SPEC, NOW) is None


def test_registry_is_unique_topic_complete_and_reviewed() -> None:
    assert len(ACCOUNTS) >= 40
    assert len({account.handle for account in ACCOUNTS}) == len(ACCOUNTS)
    assert set(REQUIRED_TOPICS) <= set(TOPICS)
    for account in ACCOUNTS:
        assert valid_handle(account.handle)
        assert account.viewpoint in VIEWPOINTS
        assert account.operator and account.reason.endswith(".")
        assert account.topic in TOPICS
        assert "bluesky" in account.tags and account.topic in account.tags
    official = {account.handle for account in ACCOUNTS if "official_issuer" in account.tags}
    state = {account.handle for account in ACCOUNTS if "state_aligned" in account.tags}
    assert {"ec.europa.eu", "ncsc.gov.uk", "who.int"} <= official
    assert "united24media.com" in state
    assert load_accounts() == ACCOUNTS


def test_registry_entries_fail_closed_on_bad_metadata() -> None:
    with pytest.raises(ValueError, match="Invalid Bluesky handle"):
        BlueskyAccount("no-dot", "Operator", "topic", "publisher", "Reason.")
    with pytest.raises(ValueError, match="unknown viewpoint"):
        BlueskyAccount("a.example", "Operator", "topic", "spokesperson", "Reason.")
    with pytest.raises(ValueError, match="required"):
        BlueskyAccount("a.example", "Operator", "topic", "publisher", "")


async def test_polling_rotates_a_bounded_slice_and_declares_its_rate() -> None:
    http = feed_http()
    poller = connector(http)
    await poller.fetch()
    await poller.fetch()
    assert len(http.requests) == 2 * ACCOUNTS_PER_CYCLE
    first = list(http.requests[:ACCOUNTS_PER_CYCLE])
    second = list(http.requests[ACCOUNTS_PER_CYCLE:])
    assert len(set(first) & set(second)) == 0
    expected = [author_feed_url(account.handle) for account in ACCOUNTS[:ACCOUNTS_PER_CYCLE]]
    assert first == expected
    # Ten accounts every fifteen minutes: forty requests an hour against one host.
    assert poller.requests_per_hour == 40
    assert SPEC.poll_interval.total_seconds() == 900
    cycles = -(-len(ACCOUNTS) // ACCOUNTS_PER_CYCLE)
    assert cycles * SPEC.poll_interval.total_seconds() <= 3 * 3600


async def test_one_failing_account_does_not_end_the_cycle() -> None:
    class PartialHttp(FakeHttp):
        async def get_json(self, url: str, *, conditional: bool = True) -> object:
            if "pravda.ua" in url:
                self.requests.append(url)
                raise FeedFetchError("upstream refused")
            return await super().get_json(url, conditional=conditional)

    http = PartialHttp({"actor=": load_fixture("bluesky_author_feed.json")})
    events = await connector(http, per_cycle=3).fetch()
    assert len(http.requests) == 3
    # Only the fixture's own account matches its posts; the others refuse the author.
    assert events and all(event.attributes["account"] == "kyivindependent.com" for event in events)


async def test_a_wholly_failed_cycle_is_reported_as_unhealthy() -> None:
    class BrokenHttp(FakeHttp):
        async def get_json(self, url: str, *, conditional: bool = True) -> object:
            self.requests.append(url)
            raise FeedFetchError("upstream refused")

    with pytest.raises(FeedFetchError):
        await connector(BrokenHttp(), per_cycle=2).fetch()


async def test_unchanged_and_empty_responses_yield_no_events() -> None:
    assert await connector(FakeHttp(not_modified=True), per_cycle=2).fetch() == []
    assert await connector(FakeHttp({"actor=": {"feed": []}}), per_cycle=1).fetch() == []
    assert await connector(FakeHttp({"actor=": {"cursor": "x"}}), per_cycle=1).fetch() == []
    assert await connector(FakeHttp({"actor=": []}), per_cycle=1).fetch() == []


def test_connector_is_registered_once_with_a_bounded_configuration() -> None:
    connectors = build_connectors(FakeHttp(), FakeClock(NOW))  # type: ignore[arg-type]
    registered = [row for row in connectors if row.spec.id == SPEC.id]
    assert len(registered) == 1
    assert registered[0].spec.reliability is Reliability.E
    assert registered[0].spec.category is Category.SOCIAL
    assert not registered[0].spec.requires_key
    assert "public posts" in SPEC.licence_note.lower() or "public api" in SPEC.licence_note.lower()
    assert SPEC.id not in {
        row.spec.id
        for row in build_connectors(FakeHttp(), FakeClock(NOW), disabled=[SPEC.id])  # type: ignore[arg-type]
    }
    with pytest.raises(ValueError, match="accounts-per-cycle"):
        BlueskyConnector(FakeHttp(), FakeClock(NOW), ACCOUNTS, per_cycle=0)  # type: ignore[arg-type]


async def test_requests_to_the_bluesky_host_are_paced_by_the_shared_pacer() -> None:
    assert DEFAULT_HOST_INTERVALS[BLUESKY_HOST] == 1.0
    now = [0.0]
    slept: list[float] = []

    async def sleep(seconds: float) -> None:
        slept.append(seconds)
        now[0] += seconds

    pacer = HostPacer(DEFAULT_HOST_INTERVALS, monotonic=lambda: now[0], sleep=sleep)
    await asyncio.gather(*[pacer.wait(author_feed_url("a.example")) for _ in range(3)])
    assert slept and sum(slept) >= 2.0
