"""Research collection budgets, cancellation, isolation and safe coverage receipts."""

import asyncio
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta

import pytest

from ase.application.research.collection import CollectionBudget, ResearchCollector
from ase.domain.events import Category, Event, Reliability
from ase.domain.research import (
    CollectionAttempt,
    CollectionStatus,
    ResearchBatch,
    ResearchMode,
    ResearchQuery,
)

NOW = datetime(2026, 9, 6, tzinfo=UTC)
QUERY = ResearchQuery("What changed?", NOW - timedelta(days=1), NOW)


def event(key: str, when: datetime = NOW - timedelta(hours=1)) -> Event:
    return Event(key, "test", Category.NEWS, "article", key, when, NOW, Reliability.F)


@dataclass
class Provider:
    id: str
    batch: ResearchBatch = field(default_factory=ResearchBatch)
    supported: bool = True
    failure: bool = False
    wait: bool = False
    called: int = 0
    cancelled: bool = False
    name: str = "Fixture feed"

    def supports(self, query: ResearchQuery) -> bool:
        return self.supported

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        self.called += 1
        if self.failure:
            raise ValueError("private query and credential must not escape")
        if self.wait:
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                self.cancelled = True
                raise
        return self.batch


async def test_budget_bounds_requests_and_preserves_unsupported_receipts() -> None:
    unsupported = Provider("unsupported", supported=False)
    first, second = Provider("first"), Provider("second")
    result = await ResearchCollector([unsupported, first, second]).collect(
        QUERY, budget=CollectionBudget(1, 1, 1, 10)
    )
    assert [attempt.status for attempt in result.attempts] == [
        CollectionStatus.UNSUPPORTED,
        CollectionStatus.EMPTY,
        CollectionStatus.BUDGET_EXHAUSTED,
    ]
    assert (unsupported.called, first.called, second.called) == (0, 1, 0)


async def test_filters_publication_dates_deduplicates_and_bounds_items() -> None:
    first = Provider(
        "first",
        ResearchBatch(
            items=(
                event("old", QUERY.since - timedelta(seconds=1)),
                event("future", QUERY.until),
                event("naive", NOW.replace(tzinfo=None)),
                event("a"),
                event("a"),
                event("b"),
                event("c"),
            )
        ),
    )
    second = Provider("second")
    result = await ResearchCollector([first, second]).collect(
        QUERY, budget=CollectionBudget(2, 1, 1, 2)
    )
    assert [item.id for item in result.items] == ["a", "b"]
    assert result.attempts[0].result_count == 2
    assert second.called == 0


async def test_safe_failure_and_timeout_continue_to_later_sources() -> None:
    failed, timed = Provider("failed", failure=True), Provider("timed", wait=True)
    last = Provider("last", ResearchBatch(items=(event("a"),)))
    result = await ResearchCollector([failed, timed, last]).collect(
        QUERY, budget=CollectionBudget(3, 1, 0.01, 10)
    )
    assert [attempt.status for attempt in result.attempts] == [
        CollectionStatus.FAILED,
        CollectionStatus.TIMED_OUT,
        CollectionStatus.COMPLETED,
    ]
    assert "credential" not in repr(result)
    assert timed.cancelled


async def test_caller_cancellation_stops_current_and_remaining_work() -> None:
    first, second = Provider("first", wait=True), Provider("second")
    task = asyncio.create_task(ResearchCollector([first, second]).collect(QUERY))
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert first.cancelled and second.called == 0


async def test_progress_and_provider_limitations_are_retained() -> None:
    seen: list[CollectionAttempt] = []

    async def progress(attempt: CollectionAttempt) -> None:
        seen.append(attempt)

    receipt = CollectionAttempt(
        "source",
        "Source",
        CollectionStatus.UNAVAILABLE,
        explanation="An operator key is required.",
        language="fr",
    )
    result = await ResearchCollector(
        [Provider("source", ResearchBatch(attempts=(receipt,)))]
    ).collect(QUERY, progress=progress)
    assert tuple(seen) == result.attempts
    assert result.attempts[0].status == CollectionStatus.UNAVAILABLE
    assert result.attempts[0].explanation == receipt.explanation


async def test_empty_period_is_not_a_positive_finding() -> None:
    provider = Provider("source", ResearchBatch(items=(event("old", NOW - timedelta(days=3)),)))
    result = await ResearchCollector([provider]).collect(QUERY)
    assert result.attempts[0].status == CollectionStatus.EMPTY
    assert "publication period" in result.attempts[0].explanation


async def test_current_snapshot_retains_real_observation_time_as_context() -> None:
    collected_at = QUERY.until + timedelta(seconds=3)
    snapshot = event("dns", collected_at).with_changes(
        observed_at=collected_at, attributes={"record_kind": "current_dns_snapshot"}
    )
    result = await ResearchCollector([Provider("dns", ResearchBatch(items=(snapshot,)))]).collect(
        QUERY
    )
    assert result.items == (snapshot,)
    assert result.items[0].published_at == collected_at
    assert "not historical-window evidence" in result.attempts[0].explanation


def test_invalid_configuration_rejected_before_collection() -> None:
    with pytest.raises(ValueError):
        ResearchCollector([Provider("same"), Provider("same")])
    with pytest.raises(ValueError):
        CollectionBudget(33, 1, 1, 10)
    with pytest.raises(ValueError):
        CollectionBudget(1, float("nan"), 1, 10)
    with pytest.raises(ValueError):
        replace(QUERY, since=NOW)
    with pytest.raises(ValueError):
        replace(QUERY, until=NOW.replace(tzinfo=None))
    with pytest.raises(ValueError):
        replace(QUERY, question=" ")
    with pytest.raises(ValueError):
        replace(QUERY, languages=())
    with pytest.raises(ValueError):
        replace(QUERY, terms=("",))
    with pytest.raises(ValueError):
        replace(QUERY, subject="x" * 301)
    assert CollectionBudget.for_mode(ResearchMode.DETAILED).requests > 6
