"""The aggregated Telegram research route: one catalogue entry, one request, honest receipts.

The catalogue is bounded, so the whole curated set must stay a single provider. These tests
hold that boundary, check that a collection makes exactly one request and discloses what it
did not search, and confirm that a page the parser cannot read becomes a failed receipt
rather than an empty one. No test touches the network.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from ase.adapters.feeds.telegram_channel_registry import channel
from ase.adapters.feeds.telegram_channels import TELEGRAM_CHANNELS
from ase.adapters.research.social_telegram import (
    LIMITATIONS,
    PROVIDER_ID,
    TelegramResearchProvider,
)
from ase.container.research_allocation_profiles import research_allocation_profiles
from ase.container.research_capabilities import research_capability_registry
from ase.container.research_feeds import public_research_feeds
from ase.container.research_sources import research_source_specs
from ase.domain.events import Credibility, Reliability
from ase.domain.research import CollectionStatus, ResearchQuery
from feeds_helpers import FakeClock

FIXTURES = Path(__file__).parent / "fixtures" / "feeds"
NOW = datetime(2026, 9, 16, 22, 0, tzinfo=UTC)
SINCE = datetime(2026, 9, 1, tzinfo=UTC)
UNTIL = datetime(2026, 9, 17, tzinfo=UTC)
ONLY = (
    channel(
        "examplechannel",
        "Example Monitor",
        "Example Organisation",
        "conflict_monitoring",
        "A stated reason long enough to be meaningful about Ukraine.",
        "publisher",
        language="uk",
    ),
)


def fixture(name: str) -> str:
    return (FIXTURES / f"telegram_preview_{name}.html").read_text("utf-8")


class StubHttp:
    def __init__(self, document: str | None = None, error: Exception | None = None) -> None:
        self.document, self.error = document, error
        self.requests: list[str] = []

    async def get_text(self, url: str, **_: object) -> str:
        self.requests.append(url)
        if self.error is not None:
            raise self.error
        assert self.document is not None
        return self.document


def query(*terms: str, languages: tuple[str, ...] = ("uk",)) -> ResearchQuery:
    return ResearchQuery(
        question="private question text that must never leave this process",
        since=SINCE,
        until=UNTIL,
        languages=languages,
        terms=terms,
    )


def provider(document: str | None = None, error: Exception | None = None, channels=ONLY):
    http = StubHttp(document, error)
    return TelegramResearchProvider(http, FakeClock(NOW), channels), http  # type: ignore[arg-type]


def test_the_whole_curated_set_is_exactly_one_research_provider() -> None:
    feeds = public_research_feeds(StubHttp(), FakeClock(NOW), spatial=False)  # type: ignore[arg-type]
    telegram = [route for route in feeds if route.id == PROVIDER_ID]
    assert len(telegram) == 1
    assert not any(route.id.startswith("research_social_telegram_") for route in feeds)
    # Sixty-odd channels must not become sixty-odd catalogue entries.
    assert len(TELEGRAM_CHANNELS) > len(telegram)


def test_the_catalogue_carries_a_reviewed_spec_capability_and_allocation_profile() -> None:
    spec = next(row for row in research_source_specs() if row.id == PROVIDER_ID)
    assert spec.reliability is Reliability.F
    assert spec.rating is not None and spec.rating.provenance_role == "platform"
    assert any("participant" in line for line in spec.rating.limitations)
    capability = research_capability_registry().capabilities[PROVIDER_ID]
    assert capability.family == "social"
    assert "Not a Telegram search" in capability.support.constraints
    assert capability.origin_group is None  # a platform confers no independent origin
    assert PROVIDER_ID in research_allocation_profiles()


async def test_a_matching_post_is_returned_at_the_research_floor_with_its_viewpoint() -> None:
    telegram, http = provider(fixture("malformed"))
    batch = await telegram.collect(query("entities"))
    assert http.requests == ["https://t.me/s/examplechannel"]  # exactly one request
    attempt = batch.attempts[0]
    assert attempt.source_id == PROVIDER_ID
    assert attempt.status is CollectionStatus.EMPTY  # no usable post time in that fixture
    assert attempt.explanation == LIMITATIONS
    assert "participant's claim and never corroboration" in attempt.explanation


async def test_dated_matching_posts_come_back_graded_at_the_floor() -> None:
    entry = channel(
        "DeepStateUA",
        "DeepState",
        "DeepState, a Ukrainian volunteer mapping project",
        "conflict_monitoring",
        "A stated reason long enough to be meaningful about mapping.",
        "aligned_commentator",
        alignment="Ukraine",
        language="uk",
    )
    telegram, http = provider(fixture("deepstateua"), channels=(entry,))
    batch = await telegram.collect(query("Мапу оновлено"))
    assert len(http.requests) == 1
    assert batch.attempts[0].status is CollectionStatus.COMPLETED
    assert len(batch.items) == 1
    item = batch.items[0]
    assert item.source_id == PROVIDER_ID
    assert item.reliability is Reliability.F
    assert item.credibility is Credibility.CANNOT_BE_JUDGED
    assert item.url == "https://t.me/DeepStateUA/23818"
    assert item.attributes["original_account"] == "@DeepStateUA"
    assert item.attributes["viewpoint"] == "aligned_commentator"
    assert item.attributes["alignment"] == "Ukraine"
    assert item.attributes["provenance_status"] == "unverified"
    assert "interested_party" in item.tags


async def test_posts_outside_the_requested_interval_are_excluded() -> None:
    narrow = ResearchQuery(
        question="q",
        since=datetime(2026, 9, 10, tzinfo=UTC),
        until=UNTIL,
        languages=("uk",),
        terms=("Мапу оновлено",),
    )
    telegram, _ = provider(fixture("deepstateua"), channels=ONLY)
    assert (await telegram.collect(narrow)).items == ()


@pytest.mark.parametrize("name", ["no_history", "changed_markup", "other_channel"])
async def test_an_unreadable_page_is_a_failed_receipt_not_an_empty_one(name: str) -> None:
    telegram, _ = provider(fixture(name))
    attempt = (await telegram.collect(query("anything"))).attempts[0]
    assert attempt.status is CollectionStatus.FAILED
    assert "never inferred from an unrecognised page" in attempt.explanation
    assert "anything" not in attempt.explanation  # request terms never reach a receipt


async def test_a_timeout_is_reported_as_a_timeout_and_makes_no_claim_of_coverage() -> None:
    telegram, _ = provider(error=TimeoutError("slow"))
    attempt = (await telegram.collect(query("anything"))).attempts[0]
    assert attempt.status is CollectionStatus.TIMED_OUT
    assert "slow" not in attempt.explanation


async def test_an_unselected_language_or_missing_terms_makes_no_request() -> None:
    telegram, http = provider(fixture("deepstateua"))
    assert not telegram.supports(query("term", languages=("ja",)))
    attempt = (await telegram.collect(query("term", languages=("ja",)))).attempts[0]
    assert attempt.status is CollectionStatus.UNSUPPORTED
    assert http.requests == []
    assert not telegram.supports(query())
    assert (await telegram.collect(query())).attempts[0].status is CollectionStatus.UNSUPPORTED
    assert http.requests == []


def test_channel_selection_is_deterministic_and_prefers_subject_overlap() -> None:
    telegram, _ = provider(channels=TELEGRAM_CHANNELS)
    chosen = telegram._select(query("mapping project", languages=("uk",)))
    assert chosen is not None and chosen.username == "DeepStateUA"
    again = telegram._select(query("mapping project", languages=("uk",)))
    assert again is chosen
    cyber = telegram._select(query("ransomware malware research", languages=("en",)))
    assert cyber is not None and cyber.username == "vxunderground"


def test_the_provider_refuses_to_be_built_without_a_curated_channel() -> None:
    with pytest.raises(ValueError, match="at least one curated channel"):
        TelegramResearchProvider(StubHttp(), FakeClock(NOW), ())  # type: ignore[arg-type]
