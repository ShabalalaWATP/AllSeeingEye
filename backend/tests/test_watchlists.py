"""Keyword scope reloads, literal queries, bounded requests and live-store publication."""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from typing import cast
from urllib.parse import parse_qs, urlsplit

import pytest

from ase.adapters.bus.memory import InMemoryEventBus
from ase.adapters.feeds.google_news import GoogleNewsWatchlistConnector, search_url
from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient
from ase.adapters.persistence.watchlists import MAX_PLANS, SqlWatchlistPlanStore
from ase.adapters.store.memory import InMemoryEventStore
from ase.application.feeds.health import HealthRegistry, SourceStatus
from ase.application.feeds.pipeline import Normaliser, Pipeline
from ase.application.feeds.scheduler import FeedScheduler
from ase.application.feeds.watchlists import (
    MAX_REQUESTS_PER_HOUR,
    MAX_WATCHLIST_TERMS,
    WatchlistBudget,
    watchlist_terms,
)
from ase.container import Container
from ase.domain.users import User
from feeds_helpers import NOW, FakeClock, FakeHttp
from watchlists_helpers import RSS, MutablePlans, plan


def test_terms_are_enabled_deduplicated_literal_and_bounded() -> None:
    terms = watchlist_terms(
        [
            plan("ignored", enabled=False),
            plan("  Air   raid ", "air RAID", 'a" OR site:internal.test "', "München & Köln", ""),
            plan("air raid", chr(92) + "safe", "x" * 90),
        ]
    )
    assert terms == ("Air raid", "a OR site:internal.test", "München & Köln", "safe", "x" * 60)
    query = parse_qs(urlsplit(search_url(terms[2])).query)
    assert query == {
        "q": ['"München & Köln" when:1d'],
        "hl": ["en-GB"],
        "gl": ["GB"],
        "ceid": ["GB:en"],
    }
    assert len(watchlist_terms([plan(*(str(i) for i in range(40)))])) == MAX_WATCHLIST_TERMS
    assert watchlist_terms([plan(" ", chr(0), '"')]) == ()


def test_budget_spaces_calls_reloads_due_terms_and_survives_quota_churn() -> None:
    budget = WatchlistBudget()
    assert budget.take(["a", "b"], NOW) == "a"
    assert budget.take(["a", "b"], NOW) is None
    assert budget.take(["a", "b"], NOW + timedelta(minutes=1)) == "b"
    assert budget.take(["a", "b"], NOW + timedelta(minutes=2)) is None
    assert budget.take(["a", "b"], NOW + timedelta(minutes=15)) == "a"
    assert budget.take([], NOW + timedelta(minutes=16)) is None
    assert budget.take(["c"], NOW + timedelta(minutes=16)) == "c"

    churn = WatchlistBudget()
    for minute in range(MAX_REQUESTS_PER_HOUR):
        assert churn.take([str(minute)], NOW + timedelta(minutes=minute)) == str(minute)
    assert churn.take(["extra"], NOW + timedelta(minutes=48)) is None
    assert churn.take(["extra"], NOW + timedelta(hours=1)) == "extra"


async def test_reload_enable_disable_edits_and_feed_ids_are_stable() -> None:
    clock = FakeClock(NOW)
    plans = MutablePlans([plan("one", "two")])
    http = FakeHttp({"news.google.com": RSS})
    connector = GoogleNewsWatchlistConnector(cast(FeedHttpClient, http), clock, plans)
    first = await connector.fetch()
    assert first[0].summary == "A plain-text summary"
    assert "watchlist" in first[0].tags
    assert "opaque" in str(first[0].url)  # Collection never resolves article links.
    assert await connector.fetch() == []
    clock.advance(timedelta(minutes=1))
    second = await connector.fetch()
    assert first[0].id == second[0].id
    assert parse_qs(urlsplit(http.requests[1]).query)["q"] == ['"two" when:1d']
    plans.plans = [replace(plans.plans[0], enabled=False)]
    clock.advance(timedelta(minutes=1))
    assert await connector.fetch() == []
    assert len(http.requests) == 2
    plans.plans = [plan("changed")]
    await connector.fetch()
    assert parse_qs(urlsplit(http.requests[-1]).query)["q"] == ['"changed" when:1d']
    assert plans.reads == 5


async def test_unmodified_feed_uses_budget_and_does_not_repeat() -> None:
    http = FakeHttp(not_modified=True)
    connector = GoogleNewsWatchlistConnector(
        cast(FeedHttpClient, http), FakeClock(NOW), MutablePlans([plan("one")])
    )
    assert await connector.fetch() == []
    assert await connector.fetch() == []
    assert len(http.requests) == 1


async def test_feed_item_cap_and_entity_rejection() -> None:
    items = "".join(f"<item><guid>{i}</guid><title>Story {i}</title></item>" for i in range(250))
    http = FakeHttp({"news.google.com": f"<rss><channel>{items}</channel></rss>"})
    connector = GoogleNewsWatchlistConnector(
        cast(FeedHttpClient, http), FakeClock(NOW), MutablePlans([plan("one")])
    )
    assert len(await connector.fetch()) == 200

    http.payloads = {
        "news.google.com": '<!DOCTYPE rss [<!ENTITY x SYSTEM "file:///secret">]><rss>&x;</rss>'
    }
    connector = GoogleNewsWatchlistConnector(
        cast(FeedHttpClient, http), FakeClock(NOW), MutablePlans([plan("one")])
    )
    with pytest.raises(FeedFetchError, match="request failed"):
        await connector.fetch()
    with pytest.raises(FeedFetchError, match="awaiting a retry"):
        await connector.fetch()


async def test_scheduler_publishes_to_live_store_and_breaks_on_failures() -> None:
    clock, store, bus, health = (
        FakeClock(NOW),
        InMemoryEventStore(),
        InMemoryEventBus(),
        HealthRegistry(),
    )
    http = FakeHttp({"news.google.com": RSS})
    connector = GoogleNewsWatchlistConnector(
        cast(FeedHttpClient, http), clock, MutablePlans([plan("private search")])
    )
    scheduler = FeedScheduler([connector], Pipeline([Normaliser()]), store, bus, health, clock)
    subscription = bus.subscribe()
    outcome = await scheduler.poll_once(connector)
    assert outcome.ok and outcome.changed == 1
    message = await subscription.__anext__()
    assert message.kind == "event.upsert"
    event = message.payload["events"][0]
    assert store.get(event.id) is not None
    subscription.close()

    http.payloads = {"news.google.com": "not XML"}
    clock.advance(timedelta(minutes=15))
    for _ in range(8):
        outcome = await scheduler.poll_once(connector)
        assert not outcome.ok
        assert "private search" not in str(outcome.error)
    assert health.get(connector.spec.id).status is SourceStatus.DISABLED
    # Waiting for a term budget must not turn a failed upstream artificially healthy.
    assert len(http.requests) == 2
    clock.advance(timedelta(minutes=15))
    http.payloads = {"news.google.com": RSS}
    scheduler.resume(connector.spec.id)
    assert (await scheduler.poll_once(connector)).ok


async def test_database_reload_is_bounded_and_observes_changes(
    container: Container, user: User
) -> None:
    source = SqlWatchlistPlanStore(container.session_factory)
    enabled = replace(plan("included"), created_by=user.id)
    disabled = replace(plan("excluded", enabled=False), created_by=user.id)
    async with container.session_factory() as session:
        repos = container.repositories(session)
        await repos.plans.add(enabled)
        await repos.plans.add(disabled)
        await repos.uow.commit()
    assert [p.id for p in await source.enabled_plans()] == [enabled.id]
    async with container.session_factory() as session:
        repos = container.repositories(session)
        await repos.plans.save(replace(enabled, enabled=False))
        await repos.plans.save(replace(disabled, enabled=True))
        await repos.uow.commit()
    assert [p.id for p in await source.enabled_plans()] == [disabled.id]
    async with container.session_factory() as session:
        repos = container.repositories(session)
        for i in range(MAX_PLANS + 1):
            await repos.plans.add(replace(plan(str(i)), created_by=user.id))
        await repos.uow.commit()
    assert len(await source.enabled_plans()) == MAX_PLANS
