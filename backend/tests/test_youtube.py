"""The keyed YouTube Data API route: channel polling, the search provider and the key gate.

None of this has been exercised against the live API, because no key exists on this
machine. The fixtures carry the documented response shapes, so these tests prove the
connector's own behaviour, not that YouTube answers as recorded.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from ase.adapters.feeds.http import FeedFetchError
from ase.adapters.feeds.registry import build_connectors
from ase.adapters.feeds.youtube import YouTubeChannelConnector, require_key, spec_for
from ase.adapters.feeds.youtube_channel_seeds import CHANNELS, load_channels
from ase.adapters.feeds.youtube_channels import (
    MAX_CHANNELS,
    TOPICS,
    YouTubeChannel,
    channel_host_intervals,
)
from ase.adapters.research.youtube import (
    DAILY_SEARCH_ALLOWANCE,
    SOURCE_ID,
    YouTubeSearchResearchProvider,
)
from ase.container.source_requirements import source_requirements
from ase.domain.events import Category, Credibility, Reliability
from ase.domain.research import CollectionStatus, ResearchQuery
from ase.domain.source_discovery import source_coverage
from ase.domain.source_rating_catalog import ANALYSIS_CHANNELS, CATALOGUE
from ase.infrastructure.settings import Settings
from feeds_helpers import FakeClock, FakeHttp, load_fixture_bytes

NOW = datetime(2026, 9, 5, 22, 30, tzinfo=UTC)
KEY = "AIzaSyTestKeyValue0000000"
BBC = next(channel for channel in CHANNELS if channel.source_id == "yt_bbc_news")
PERUN = next(channel for channel in CHANNELS if channel.source_id == "yt_perun")
PAYLOADS = {
    "/channels?": load_fixture_bytes("youtube_channels.json"),
    "/playlistItems?": load_fixture_bytes("youtube_playlist_items.json"),
    "/search?": load_fixture_bytes("youtube_search.json"),
}


def connector(channel: YouTubeChannel = BBC, payloads: dict[str, object] | None = None):
    http = FakeHttp(dict(payloads or PAYLOADS))
    return YouTubeChannelConnector(http, FakeClock(NOW), KEY, channel), http


async def test_channel_poll_resolves_uploads_once_then_costs_one_unit_a_poll() -> None:
    poller, http = connector()
    first = await poller.fetch()
    second = await poller.fetch()
    # channels.list once, then playlistItems.list per poll: 1 quota unit each.
    assert len(http.requests) == 3
    assert "/channels?" in http.requests[0] and "forHandle" not in http.requests[0]
    assert "id=UC16niRr50-MSBwiO3YDb3RA" in http.requests[0]
    assert all("/playlistItems?" in url for url in http.requests[1:])
    assert "playlistId=UU16niRr50-MSBwiO3YDb3RA" in http.requests[1]
    assert [event.id for event in first] == [event.id for event in second]
    # Private items, items with no video identity and repeated uploads are one event.
    assert len(first) == 1


async def test_channel_video_keeps_only_title_time_identity_and_a_bounded_excerpt() -> None:
    poller, _ = connector()
    event = (await poller.fetch())[0]
    assert event.source_id == "yt_bbc_news" and event.subtype == "video"
    assert event.category is Category.SOCIAL
    assert event.title == "Drone strike reported near Odesa"
    assert event.url == "https://www.youtube.com/watch?v=aBcDeFgHiJk"
    # contentDetails.videoPublishedAt is publication; snippet.publishedAt is playlist order.
    assert event.published_at == datetime(2026, 9, 5, 21, 40, tzinfo=UTC)
    assert event.summary is not None and len(event.summary) <= 500
    assert event.reliability is Reliability.B
    assert event.credibility is Credibility.POSSIBLY_TRUE
    assert event.attributes["video_id"] == "aBcDeFgHiJk"
    assert event.attributes["instance"] == "BBC News"
    assert event.point is None and "youtube" in event.tags


async def test_analysis_channel_sits_at_doctrines_floor_and_resolves_by_handle() -> None:
    poller, http = connector(PERUN)
    event = (await poller.fetch())[0]
    assert "forHandle=PerunAU" in http.requests[0] and "@" not in http.requests[0]
    assert event.reliability is Reliability.E
    assert event.credibility is Credibility.CANNOT_BE_JUDGED
    assert "not corroborated" in event.grade_rationale
    assert {"drones", "defence_analysis"} <= event.tags


def test_state_run_channel_is_tagged_state_aligned_and_treated_as_a_position() -> None:
    cgtn = next(channel for channel in CHANNELS if channel.source_id == "yt_cgtn")
    assert cgtn.state_aligned and "state_controlled" in cgtn.tags
    assert cgtn.credibility is Credibility.DOUBTFUL
    assert "state_controlled" in spec_for(cgtn).flags


async def test_an_unresolvable_channel_fails_its_own_poll_without_a_playlist_request() -> None:
    poller, http = connector(payloads={"/channels?": b'{"kind":"x","items":[]}'})
    with pytest.raises(FeedFetchError, match="uploads playlist"):
        await poller.fetch()
    assert len(http.requests) == 1


@pytest.mark.parametrize(
    "payload", [b"not json", b"[]", b'{"items":[{"contentDetails":{"relatedPlaylists":{}}}]}']
)
async def test_unusable_responses_are_refused_rather_than_partly_trusted(payload: bytes) -> None:
    poller, _ = connector(payloads={"/channels?": payload})
    with pytest.raises(FeedFetchError):
        await poller.fetch()


def test_the_configured_key_never_reaches_a_repr_and_bad_keys_are_refused() -> None:
    poller, _ = connector()
    assert KEY not in repr(poller) and poller.spec.id in repr(poller)
    for invalid in ("", "short", "has spaces in it at all", "a" * 200):
        with pytest.raises(ValueError, match="YouTube Data API key"):
            require_key(invalid)


def test_the_reviewed_channel_list_is_bounded_distinct_and_covers_the_asked_topics() -> None:
    channels = load_channels()
    assert 0 < len(channels) <= MAX_CHANNELS
    assert len({channel.source_id for channel in channels}) == len(channels)
    assert len({channel.handle.lower() for channel in channels}) == len(channels)
    covered = {topic for channel in channels for topic in channel.topics}
    assert covered == TOPICS
    # The six broadcasters the retired Atom feeds carried are all still present.
    assert {
        "yt_bbc_news",
        "yt_reuters",
        "yt_dw_news",
        "yt_al_jazeera",
        "yt_france24",
        "yt_sky_news",
    } <= {channel.source_id for channel in channels}
    assert channel_host_intervals() == {"www.googleapis.com": 1.0}


def test_every_channel_has_a_reviewed_grade_and_catalogued_coverage() -> None:
    for channel in load_channels():
        rating = spec_for(channel).rating
        assert rating is not None and rating.basis and rating.limitations
        assert source_coverage(channel.source_id).scope != "unspecified", channel.source_id
        if channel.kind == "analysis":
            assert channel.source_id in ANALYSIS_CHANNELS
            assert rating.status == "unassessed" and channel.reliability is Reliability.E
        else:
            assert CATALOGUE[channel.source_id].grade == channel.reliability.value


@pytest.mark.parametrize(
    "change",
    [
        {"source_id": "reddit_worldnews"},
        {"handle": "no-at-sign"},
        {"channel_id": "not-a-channel"},
        {"topics": ("weather",)},
        {"topics": ()},
        {"minutes": 1},
        {"kind": "official", "state_aligned": True},
    ],
)
def test_a_malformed_channel_row_is_refused_as_a_packaging_fault(change: dict) -> None:
    with pytest.raises(ValueError):
        replace(BBC, **change)


def test_no_youtube_connector_exists_until_the_operator_supplies_a_key() -> None:
    without = {c.spec.id for c in build_connectors(FakeHttp(), FakeClock(NOW))}  # type: ignore[arg-type]
    assert not any(id_.startswith("yt_") for id_ in without)
    with_key = build_connectors(FakeHttp(), FakeClock(NOW), youtube_api_key=KEY)  # type: ignore[arg-type]
    ids = {c.spec.id for c in with_key}
    assert {channel.source_id for channel in load_channels()} <= ids
    assert all(c.spec.requires_key for c in with_key if c.spec.id.startswith("yt_"))
    excluded = build_connectors(  # type: ignore[arg-type]
        FakeHttp(), FakeClock(NOW), ("yt_bbc_news",), youtube_api_key=KEY
    )
    assert "yt_bbc_news" not in {c.spec.id for c in excluded}


def test_a_missing_key_is_reported_as_the_documented_setting() -> None:
    requirements = source_requirements(Settings(youtube_api_key=None))
    for source_id in (*(c.source_id for c in load_channels()), SOURCE_ID):
        requirement = requirements[source_id]
        assert requirement.satisfied is False and not requirement.optional
        assert requirement.setting == "ASE_YOUTUBE_API_KEY"
    present = source_requirements(Settings(youtube_api_key=KEY))  # type: ignore[arg-type]
    assert present["yt_bbc_news"].satisfied is True


def query(**changes: object) -> ResearchQuery:
    base = ResearchQuery(
        "A private research question",
        NOW - timedelta(days=2),
        NOW,
        terms=("rail disruption", "sabotage"),
    )
    return replace(base, **changes)  # type: ignore[arg-type]


async def test_research_search_is_one_request_with_explicit_phrases_and_dates() -> None:
    http = FakeHttp(dict(PAYLOADS))
    provider = YouTubeSearchResearchProvider(http, FakeClock(NOW), KEY)
    batch = await provider.collect(query())
    assert len(http.requests) == 1
    url = http.requests[0]
    assert "/search?" in url and "maxResults=20" in url and "order=date" in url
    assert "A+private+research+question" not in url
    assert "publishedAfter=2026-09-03T22" in url and "publishedBefore=2026-09-05T22" in url
    assert len(batch.items) == 1
    item = batch.items[0]
    assert item.source_id == SOURCE_ID and item.reliability is Reliability.F
    assert item.credibility is Credibility.CANNOT_BE_JUDGED
    assert item.url == "https://www.youtube.com/watch?v=Qw3rTy7uIoP"
    assert item.attributes["original_account"] == "An uploader"
    assert batch.attempts[0].status is CollectionStatus.COMPLETED
    assert "not a channel-curated or complete" in batch.attempts[0].explanation


@pytest.mark.parametrize(
    ("changes", "status"),
    [
        ({"terms": ()}, CollectionStatus.UNSUPPORTED),
        (
            {"terms": tuple(f"{i} " + "phrase " * 12 for i in range(12))},
            CollectionStatus.UNSUPPORTED,
        ),
        ({"since": NOW, "until": NOW + timedelta(days=1)}, CollectionStatus.EMPTY),
    ],
)
async def test_unsupported_and_out_of_interval_results_make_honest_receipts(
    changes: dict, status: CollectionStatus
) -> None:
    http = FakeHttp(dict(PAYLOADS))
    provider = YouTubeSearchResearchProvider(http, FakeClock(NOW), KEY)
    batch = await provider.collect(query(**changes))
    assert batch.attempts[0].status is status and not batch.items
    assert bool(http.requests) is (status is not CollectionStatus.UNSUPPORTED)


async def test_research_without_a_key_reports_the_gate_and_makes_no_request() -> None:
    http = FakeHttp(dict(PAYLOADS))
    provider = YouTubeSearchResearchProvider(http, FakeClock(NOW))
    batch = await provider.collect(query())
    assert batch.attempts[0].status is CollectionStatus.UNAVAILABLE
    assert "robots.txt" in batch.attempts[0].explanation
    assert not http.requests and not batch.items


async def test_the_daily_search_allowance_protects_scheduled_channel_collection() -> None:
    http = FakeHttp(dict(PAYLOADS))
    provider = YouTubeSearchResearchProvider(http, FakeClock(NOW), KEY)
    for _ in range(DAILY_SEARCH_ALLOWANCE):
        await provider.collect(query())
    spent = await provider.collect(query())
    assert spent.attempts[0].status is CollectionStatus.BUDGET_EXHAUSTED
    assert len(http.requests) == DAILY_SEARCH_ALLOWANCE
    assert KEY not in repr(provider) and KEY not in repr(spent)


async def test_a_failed_search_is_a_receipt_not_an_exception_or_a_leaked_url() -> None:
    http = FakeHttp({"/search?": b"not json at all"})
    provider = YouTubeSearchResearchProvider(http, FakeClock(NOW), KEY)
    batch = await provider.collect(query())
    assert batch.attempts[0].status is CollectionStatus.FAILED and not batch.items
    assert KEY not in repr(batch) and "rail disruption" not in repr(batch)
