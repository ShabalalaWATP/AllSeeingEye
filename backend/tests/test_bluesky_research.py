"""The single aggregated Bluesky research route: selection, bounds, receipts and wiring."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ase.adapters.feeds.bluesky import SPEC
from ase.adapters.feeds.bluesky_accounts import ACCOUNTS
from ase.adapters.feeds.http import FeedFetchError
from ase.adapters.research.social_bluesky import (
    LIMITATIONS,
    MAX_ACCOUNTS,
    PROVIDER_ID,
    BlueskyResearchProvider,
    selected_accounts,
)
from ase.container.research_allocation_profiles import research_allocation_profiles
from ase.container.research_capabilities import research_capability_registry
from ase.container.research_feeds import public_research_feeds
from ase.container.research_sources import research_source_specs
from ase.domain.events import Category, Credibility, Reliability
from ase.domain.research import CollectionStatus, ResearchQuery
from ase.domain.source_capabilities import CapabilityScope, ExecutionRoute
from feeds_helpers import FakeClock, FakeHttp, load_fixture

NOW = datetime(2026, 9, 5, 22, 30, tzinfo=UTC)
CLOCK = FakeClock(NOW)
QUERY = ResearchQuery(
    question="A private analytical question that must never reach the upstream request",
    since=datetime(2026, 9, 5, tzinfo=UTC),
    until=datetime(2026, 9, 6, tzinfo=UTC),
    terms=("air defence", "Ukraine"),
)


def provider(http: FakeHttp) -> BlueskyResearchProvider:
    return BlueskyResearchProvider(http, CLOCK, ACCOUNTS)  # type: ignore[arg-type]


def feed_http() -> FakeHttp:
    return FakeHttp({"actor=": load_fixture("bluesky_author_feed.json")})


def test_topic_words_select_a_bounded_slice_of_the_registry() -> None:
    ukraine = selected_accounts(("Ukraine strikes",))
    assert len(ukraine) == MAX_ACCOUNTS
    assert all(account.topic == "ukraine_russia" for account in ukraine)
    assert all(account.topic == "cyber_threat_intel" for account in selected_accounts(("malware",)))
    assert all(account.topic == "drones_uncrewed" for account in selected_accounts(("UAV",)))
    # An unmatched phrase falls back to the general news accounts, never to the whole list.
    fallback = selected_accounts(("a phrase about nothing in particular",))
    assert 0 < len(fallback) <= MAX_ACCOUNTS
    assert all(account.topic == "global_news" for account in fallback)
    assert len(selected_accounts(("Ukraine drones cyber energy space",))) == MAX_ACCOUNTS


async def test_collection_reads_curated_accounts_and_matches_phrases_locally() -> None:
    http = feed_http()
    batch = await provider(http).collect(QUERY)
    assert len(http.requests) == MAX_ACCOUNTS
    assert all("public.api.bsky.app" in url for url in http.requests)
    assert not any(QUERY.question[:20] in url for url in http.requests)
    assert len(batch.attempts) == 1
    attempt = batch.attempts[0]
    assert attempt.source_id == PROVIDER_ID and attempt.status is CollectionStatus.COMPLETED
    assert attempt.explanation == LIMITATIONS and attempt.result_count == len(batch.items)
    assert batch.items
    for item in batch.items:
        assert item.source_id == PROVIDER_ID and item.category is Category.SOCIAL
        assert item.reliability is Reliability.F
        assert item.credibility is Credibility.CANNOT_BE_JUDGED
        assert str(item.url).startswith("https://bsky.app/profile/")
        assert QUERY.since <= (item.published_at or NOW) < QUERY.until
        assert "unassessed" in item.grade_rationale
    titles = " ".join(item.title.lower() for item in batch.items)
    assert "air defence" in titles or "ukraine" in titles


async def test_posts_outside_the_interval_or_without_a_phrase_are_not_returned() -> None:
    outside = ResearchQuery(
        question="Interval outside the fixture",
        since=datetime(2026, 8, 1, tzinfo=UTC),
        until=datetime(2026, 8, 2, tzinfo=UTC),
        terms=("air defence",),
    )
    batch = await provider(feed_http()).collect(outside)
    assert batch.items == () and batch.attempts[0].status is CollectionStatus.EMPTY
    unmatched = ResearchQuery(
        question="A phrase the fixture never uses",
        since=QUERY.since,
        until=QUERY.until,
        terms=("submarine cable repair ship",),
    )
    assert (await provider(feed_http()).collect(unmatched)).items == ()


async def test_missing_phrases_make_no_request_at_all() -> None:
    http = feed_http()
    bare = ResearchQuery(question="No explicit phrases", since=QUERY.since, until=QUERY.until)
    batch = await provider(http).collect(bare)
    assert http.requests == []
    assert batch.attempts[0].status is CollectionStatus.UNSUPPORTED
    assert not provider(http).supports(bare) and provider(http).supports(QUERY)


async def test_a_failed_read_never_leaks_upstream_text() -> None:
    class BrokenHttp(FakeHttp):
        async def get_json(self, url: str, *, conditional: bool = True) -> object:
            self.requests.append(url)
            raise FeedFetchError(f"secret upstream detail for {url}")

    batch = await provider(BrokenHttp()).collect(QUERY)
    attempt = batch.attempts[0]
    assert attempt.status is CollectionStatus.FAILED and not batch.items
    assert "secret upstream detail" not in attempt.explanation
    assert "could not be read" in attempt.explanation


async def test_empty_and_malformed_payloads_report_empty_coverage() -> None:
    for payload in ({"feed": []}, {"cursor": "x"}, []):
        batch = await provider(FakeHttp({"actor=": payload})).collect(QUERY)
        assert batch.items == () and batch.attempts[0].status is CollectionStatus.EMPTY


def test_the_catalogue_gains_exactly_one_reviewed_bluesky_route() -> None:
    providers = public_research_feeds(FakeHttp(), CLOCK, spatial=False)  # type: ignore[arg-type]
    assert [row.id for row in providers].count(PROVIDER_ID) == 1
    assert PROVIDER_ID in {row.id for row in public_research_feeds(FakeHttp(), CLOCK, spatial=True)}  # type: ignore[arg-type]
    specs = {spec.id: spec for spec in research_source_specs()}
    spec = specs[PROVIDER_ID]
    assert spec.category is Category.SOCIAL and spec.reliability is Reliability.F
    assert spec.rating is not None and spec.rating.provenance_role == "platform"
    assert not spec.requires_key
    assert SPEC.licence_note in spec.rating.limitations
    assert PROVIDER_ID not in {row.id for row in research_source_specs(disabled=(SPEC.id,))}
    # One aggregated route, not one per curated account.
    assert len([key for key in specs if key.startswith("research_social_")]) < len(ACCOUNTS)
    capability = research_capability_registry().capabilities[PROVIDER_ID]
    assert capability.family == "social" and capability.origin_group is None
    assert capability.route is ExecutionRoute.PUBLIC_RESEARCH
    assert CapabilityScope.AREA not in capability.support.scopes
    assert "three reviewed public accounts" in capability.support.constraints
    profile = research_allocation_profiles()[PROVIDER_ID]
    assert not profile.primary_content and not profile.local_language
    assert "drone drones" in profile.terms and len(profile.terms) <= 24


def test_the_provider_refuses_an_empty_registry() -> None:
    with pytest.raises(ValueError, match="reviewed accounts"):
        BlueskyResearchProvider(FakeHttp(), CLOCK, ())  # type: ignore[arg-type]
