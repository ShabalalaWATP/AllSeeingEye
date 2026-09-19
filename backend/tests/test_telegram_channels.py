"""Curated Telegram coverage: grading, labelling, refusal handling, pacing and wiring.

Grading is the point of this feature, so most of what is asserted here is that nothing in
the curated set can quietly acquire authority: every post is at doctrine's floor, every
government, armed force and state outlet is tagged the way the state-aligned news feeds
are, and a page the parser cannot read stops collection with a stated reason instead of
producing an empty or wrong result. No test touches the network.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ase.adapters.feeds.host_pacing import DEFAULT_HOST_INTERVALS, TELEGRAM_HOST, HostPacer
from ase.adapters.feeds.http_contracts import (
    FeedFetchError,
    FeedHttpStatusError,
    FeedRateLimitedError,
    NotModified,
)
from ase.adapters.feeds.registry import build_connectors
from ase.adapters.feeds.telegram import (
    REFUSED_REASON,
    REFUSED_RECHECK,
    UNAVAILABLE_RECHECK,
    TelegramChannelConnector,
    channel_spec,
)
from ase.adapters.feeds.telegram_channel_registry import TOPICS, TelegramChannel, channel
from ase.adapters.feeds.telegram_channels import TELEGRAM_CHANNELS, telegram_channels
from ase.application.ports.feed_diagnostics import FeedBlocked
from ase.domain.events import Category, Credibility, Reliability
from ase.domain.social import PLATFORMS, platform_groups
from ase.domain.source_ratings import source_rating_for
from feeds_helpers import FakeClock

FIXTURES = Path(__file__).parent / "fixtures" / "feeds"
NOW = datetime(2026, 9, 16, 22, 0, tzinfo=UTC)
DEEPSTATE = next(entry for entry in TELEGRAM_CHANNELS if entry.username == "DeepStateUA")


def fixture(name: str) -> str:
    return (FIXTURES / f"telegram_preview_{name}.html").read_text("utf-8")


class StubHttp:
    """Serves one recorded page, or raises, and records every URL it was asked for."""

    def __init__(self, document: str | None = None, error: Exception | None = None) -> None:
        self.document, self.error = document, error
        self.requests: list[str] = []

    async def get_text(self, url: str, **_: object) -> str:
        self.requests.append(url)
        if self.error is not None:
            raise self.error
        assert self.document is not None
        return self.document


def connector(document: str | None = None, error: Exception | None = None, entry=DEEPSTATE):
    http = StubHttp(document, error)
    return TelegramChannelConnector(http, FakeClock(NOW), entry), http  # type: ignore[arg-type]


# --- the registry itself -----------------------------------------------------------


def test_every_curated_channel_is_declared_completely_and_uniquely() -> None:
    assert 30 <= len(TELEGRAM_CHANNELS) <= 80
    usernames = [entry.username.casefold() for entry in TELEGRAM_CHANNELS]
    assert len(set(usernames)) == len(usernames)
    for entry in TELEGRAM_CHANNELS:
        assert entry.topic in TOPICS
        assert entry.operator and entry.name and len(entry.reason) >= 20
        assert entry.source_id == f"telegram_{entry.username.casefold()}"
        assert 30 <= entry.poll_minutes <= 240


def test_the_registry_refuses_an_entry_it_cannot_describe() -> None:
    good = {
        "username": "examplechannel",
        "name": "Example",
        "operator": "Example Organisation",
        "topic": "conflict_monitoring",
        "reason": "A stated reason long enough to be meaningful.",
        "viewpoint": "publisher",
    }
    for broken in (
        {"username": "no"},
        {"username": "has spaces"},
        {"topic": "not_a_topic"},
        {"viewpoint": "trustworthy"},
        {"reason": "too short"},
        {"operator": ""},
        {"poll_minutes": 5},
        {"poll_minutes": 1440},
    ):
        with pytest.raises(ValueError):
            TelegramChannel(**{**good, **broken})  # type: ignore[arg-type]


def test_both_sides_of_the_ukraine_war_are_carried_and_labelled() -> None:
    topics = {entry.topic for entry in TELEGRAM_CHANNELS}
    assert {"ukraine_official", "russia_official", "russia_milblogger"} <= topics
    assert len(topics) >= 10  # real breadth, not one region with a token gesture
    ukrainian = [e for e in TELEGRAM_CHANNELS if e.alignment == "Ukraine"]
    russian = [e for e in TELEGRAM_CHANNELS if e.alignment == "Russia"]
    assert len(ukrainian) >= 8 and len(russian) >= 8
    # An armed force's own channel is an interested party, never an observer.
    for entry in TELEGRAM_CHANNELS:
        if entry.topic in {"ukraine_official", "russia_official", "russia_milblogger"}:
            assert "interested_party" in entry.viewpoint_tags


def test_state_run_channels_carry_the_tags_the_interface_already_marks() -> None:
    for entry in TELEGRAM_CHANNELS:
        if entry.viewpoint == "official_issuer":
            assert entry.viewpoint_tags == frozenset({"official_issuer", "interested_party"})
        elif entry.viewpoint == "state_media":
            assert entry.viewpoint_tags == frozenset({"state_aligned", "interested_party"})
        assert entry.state_aligned == (entry.viewpoint in {"official_issuer", "state_media"})
    marked = {e.username for e in TELEGRAM_CHANNELS if "state_aligned" in e.viewpoint_tags}
    assert {"tass_agency", "rian_ru", "rybar", "PressTV", "irna_1313"} <= marked
    issuers = {e.username for e in TELEGRAM_CHANNELS if e.viewpoint == "official_issuer"}
    assert {"mod_russia", "generalstaffZSU", "idfofficial", "MID_Russia"} <= issuers


def test_disabling_a_source_id_removes_that_channel() -> None:
    disabled = frozenset({DEEPSTATE.source_id})
    remaining = telegram_channels(disabled)
    assert len(remaining) == len(TELEGRAM_CHANNELS) - 1
    assert DEEPSTATE not in remaining


# --- grading and labelling of collected posts --------------------------------------


def test_every_channel_specification_sits_at_the_social_floor() -> None:
    for entry in TELEGRAM_CHANNELS:
        spec = channel_spec(entry)
        assert spec.reliability is Reliability.E
        assert spec.category is Category.SOCIAL
        assert spec.url == f"https://t.me/s/{entry.username}"
        assert spec.poll_interval >= timedelta(minutes=30)
        assert "no media" in spec.licence_note
        rating = source_rating_for(spec.id, spec.reliability)
        assert rating.status == "unassessed" and rating.assessed_grade is None
        assert rating.provenance_role == "platform"


async def test_a_recorded_channel_preview_becomes_floor_graded_social_events() -> None:
    telegram, http = connector(fixture("deepstateua"))
    events = await telegram.fetch()
    assert http.requests == ["https://t.me/s/DeepStateUA"]
    assert len(events) == 2
    first = events[0]
    assert first.category is Category.SOCIAL and first.subtype == "post"
    assert first.reliability is Reliability.E
    assert first.credibility is Credibility.CANNOT_BE_JUDGED
    assert "neither the channel nor the claim is independently assessed" in first.grade_rationale
    assert {"telegram", "conflict_monitoring", "interested_party"} <= first.tags
    assert first.url == "https://t.me/DeepStateUA/23818"
    assert first.published_at == datetime(2026, 9, 9, 15, 20, 1, tzinfo=UTC)
    assert first.attributes["account"] == "@DeepStateUA"
    assert first.attributes["operator"] == DEEPSTATE.operator
    assert first.attributes["viewpoint"] == "aligned_commentator"
    assert first.attributes["media"] == 0 and first.attributes["excerpt_only"] is True
    assert "<" not in (first.summary or "") and len(first.title) <= 140
    assert first.point is None  # a post says nothing reliable about where it happened


async def test_posts_group_under_their_own_platform_and_channel() -> None:
    telegram, _ = connector(fixture("deepstateua"))
    groups = platform_groups(await telegram.fetch())
    assert "telegram" in PLATFORMS
    assert groups[0].platform == "telegram"
    assert groups[0].instance == "t.me/DeepStateUA"


# --- failure modes -----------------------------------------------------------------


@pytest.mark.parametrize("status", [401, 403, 404, 410, 451])
async def test_a_refusal_defers_with_fixed_operator_text(status: int) -> None:
    telegram, http = connector(error=FeedHttpStatusError(status, "https://t.me/s/DeepStateUA"))
    with pytest.raises(FeedBlocked) as caught:
        await telegram.fetch()
    assert str(caught.value) == REFUSED_REASON
    assert "imitate a browser" in str(caught.value)
    assert "t.me" not in str(caught.value)  # no URL or response body in operator-facing text
    assert caught.value.retry_at == NOW + REFUSED_RECHECK == NOW + timedelta(hours=12)
    assert len(http.requests) == 1


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("no_history", "private, removed"),
        ("changed_markup", "markup has probably changed"),
        ("other_channel", "none belonged to this channel"),
    ],
)
async def test_an_unreadable_page_defers_instead_of_collecting_nothing(
    name: str, expected: str
) -> None:
    entry = channel(
        "examplechannel",
        "Example",
        "Example Organisation",
        "conflict_monitoring",
        "A stated reason long enough to be meaningful.",
        "publisher",
    )
    telegram, _ = connector(fixture(name), entry=entry)
    with pytest.raises(FeedBlocked) as caught:
        await telegram.fetch()
    assert expected in str(caught.value)
    assert "never guessed" in str(caught.value)
    assert caught.value.retry_at == NOW + UNAVAILABLE_RECHECK


async def test_rate_limiting_and_other_failures_are_left_to_the_scheduler() -> None:
    limited, _ = connector(error=FeedRateLimitedError("https://t.me/s/x", timedelta(minutes=5)))
    with pytest.raises(FeedRateLimitedError):
        await limited.fetch()
    broken, _ = connector(error=FeedFetchError("Feed request failed."))
    with pytest.raises(FeedFetchError):
        await broken.fetch()
    server, _ = connector(error=FeedHttpStatusError(503, "https://t.me/s/x"))
    with pytest.raises(FeedHttpStatusError):
        await server.fetch()


async def test_an_unchanged_page_produces_no_events() -> None:
    telegram, _ = connector(error=NotModified("https://t.me/s/DeepStateUA"))
    assert await telegram.fetch() == []


# --- politeness and wiring ---------------------------------------------------------


async def test_requests_to_telegram_are_spaced_by_the_shared_host_pacer() -> None:
    assert DEFAULT_HOST_INTERVALS[TELEGRAM_HOST] == 5.0
    slept: list[float] = []
    now = [0.0]

    async def sleep(delay: float) -> None:
        slept.append(delay)
        now[0] += delay

    pacer = HostPacer(DEFAULT_HOST_INTERVALS, monotonic=lambda: now[0], sleep=sleep)
    await pacer.wait("https://t.me/s/DeepStateUA")
    now[0] += 1.0
    await pacer.wait("https://t.me/s/mod_russia")
    await pacer.wait("https://t.me/s/DeepStateUA")
    assert slept == [pytest.approx(4.0), pytest.approx(5.0)]
    assert now[0] == pytest.approx(10.0)


def test_the_curated_set_stays_within_a_polite_request_rate() -> None:
    per_hour = sum(60 / entry.poll_minutes for entry in TELEGRAM_CHANNELS)
    assert per_hour < 90  # roughly one request a minute to a single upstream host


def test_the_connector_set_registers_one_connector_for_each_curated_channel() -> None:
    connectors = build_connectors(StubHttp(), FakeClock(NOW))  # type: ignore[arg-type]
    ids = [c.spec.id for c in connectors if c.spec.id.startswith("telegram_")]
    assert ids == [entry.source_id for entry in TELEGRAM_CHANNELS]
    disabled = build_connectors(
        StubHttp(),  # type: ignore[arg-type]
        FakeClock(NOW),
        [DEEPSTATE.source_id],
    )
    assert DEEPSTATE.source_id not in {c.spec.id for c in disabled}
