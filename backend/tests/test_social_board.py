"""Social aggregation boundaries, bounded history and private collection vocabulary."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from ase.adapters.persistence.models import ActivitySampleRow
from ase.adapters.persistence.social import KIND_SOCIAL, SqlSocialActivity, SqlSocialTerms
from ase.adapters.store.memory import InMemoryEventStore
from ase.application.trackers.social import SocialMonitor, SocialService
from ase.container import Container
from ase.domain.social import (
    MAX_TERMS,
    KeywordActivity,
    SocialBaseline,
    WatchedTerm,
    keyword_counts,
    platform_groups,
    top_hashtags,
    vocabulary,
)
from ase.domain.users import User
from feeds_helpers import NOW, make_event
from helpers import USER_EMAIL, USER_PASSWORD, FakeClock, bearer, login_token
from social_helpers import FixedTerms, MemoryActivity, social_plan, social_post


def test_vocabulary_bounds_and_private_ownership() -> None:
    owner, another = uuid4(), uuid4()
    terms = vocabulary(
        ["#Ukraine", " UKRAINE ", ""],
        [
            social_plan(owner, ["Secret", "Ukraine", ""]),
            social_plan(another, ["Secret"]),
            social_plan(owner, ["Disabled"], enabled=False),
        ],
    )
    assert [term.term for term in terms] == ["ukraine", "secret"]
    assert terms[0].public and terms[1].owners == frozenset({owner, another})
    assert len(terms[0].key) == 32 and "ukraine" not in terms[0].key
    bounded = vocabulary([f"term{i:02}" for i in range(100)], [])
    assert len(bounded) == MAX_TERMS and bounded[-1].term == "term31"


def test_keyword_counts_use_word_boundaries_and_count_each_post_once() -> None:
    terms = vocabulary(["war", "c++", "台湾", "new york"], [])
    events = [
        social_post("a", "WAR war warfare c++ 台湾 New York"),
        social_post("b", "Beware warfare"),
    ]
    counts = keyword_counts(events, terms)
    assert all(counts[term.key] == 1 for term in terms)
    assert set(keyword_counts([], terms).values()) == {0}


def test_hashtags_are_deduplicated_and_platforms_keep_locations() -> None:
    posts = [
        social_post("a", "#Ukraine #ukraine #тайвань"),
        social_post("b").with_changes(tags=frozenset({"reddit"}), point=None),
        social_post("c").with_changes(tags=frozenset({"youtube"})),
        social_post("d").with_changes(tags=frozenset(), attributes={}),
        social_post("e").with_changes(attributes={}),
    ]
    assert top_hashtags(posts)[0].tag == "ukraine" and top_hashtags(posts)[0].count == 5
    assert [row.tag for row in top_hashtags(posts, 1)] == ["ukraine"]
    groups = platform_groups(posts)
    assert sum(group.count for group in groups) == 5
    assert sum(group.located for group in groups) == 4
    assert next(group for group in groups if group.platform == "other").instance == "test_source"
    assert any(group.instance == "test_source" and group.platform == "mastodon" for group in groups)


@pytest.mark.parametrize(
    ("count", "mean", "hours", "burst", "ratio"),
    [
        (4, None, 0, False, None),
        (4, 1, 5, False, 4),
        (2, 1, 6, False, 2),
        (3, 2, 6, False, 1.5),
        (4, 2, 6, True, 2),
        (3, 0, 6, True, None),
        (0, 0, 6, False, None),
    ],
)
def test_burst_needs_history_and_multiple_posts(
    count: int, mean: float | None, hours: int, burst: bool, ratio: float | None
) -> None:
    row = KeywordActivity("test", count, mean, hours)
    assert row.burst is burst and row.ratio == ratio


async def test_board_uses_rolling_day_complete_hour_and_owner_terms(
    user: User, admin: User
) -> None:
    store = InMemoryEventStore()
    watch = WatchedTerm("ukraine", True)
    private = WatchedTerm("private", False, frozenset({admin.id}))
    terms = FixedTerms((watch, private))
    activity = MemoryActivity()
    activity.means = {watch.key: SocialBaseline(1.5, 8)}
    store.upsert(
        [social_post(str(i)) for i in range(3)]
        + [
            social_post("older", when=NOW - timedelta(hours=25)),
            social_post("future", when=NOW + timedelta(hours=1)),
            social_post("boundary").with_changes(published_at=NOW - timedelta(hours=24)),
            make_event("other"),
        ]
    )
    service = SocialService(store, terms, activity, FakeClock(NOW))
    board = await service.board(user)
    assert board.total == 4 and len(board.posts) == 4 and board.located == 4
    assert len(board.keywords) == 1 and board.keywords[0].burst
    assert board.keywords[0].count == 3
    assert activity.queries[0][1] == NOW - timedelta(hours=1)
    assert activity.queries[0][0] == NOW - timedelta(days=30)
    assert len((await service.board(admin)).keywords) == 2


async def test_monitor_counts_only_previous_hour_and_recovers_from_failure() -> None:
    store = InMemoryEventStore()
    term, quiet = WatchedTerm("ukraine", True), WatchedTerm("quiet", True)
    activity = MemoryActivity()
    store.upsert(
        [
            social_post("a"),
            social_post("old", when=NOW - timedelta(hours=1)),
            social_post("new").with_changes(published_at=NOW),
        ]
    )
    sampled = asyncio.Event()
    sleeps: list[float] = []

    async def sleep(seconds: float) -> None:
        sleeps.append(seconds)
        if len(sleeps) == 2:
            sampled.set()
        await asyncio.sleep(0)

    monitor = SocialMonitor(store, FixedTerms((term, quiet)), activity, FakeClock(NOW), sleep=sleep)
    assert await monitor.sample() == 1
    assert activity.rows[NOW - timedelta(hours=1)] == {term.key: 1, quiet.key: 0}
    activity.fail = True
    await monitor.start()
    await monitor.start()
    await asyncio.wait_for(sampled.wait(), timeout=2)
    await monitor.stop()
    await monitor.stop()
    assert sleeps[0] == 300


async def test_sql_samples_keep_zeroes_exclude_current_hour_and_prune(container: Container) -> None:
    activity = SqlSocialActivity(container.session_factory)
    term, removed = WatchedTerm("ukraine", True), WatchedTerm("removed", True)
    async with container.session_factory() as session:
        baselines = container.repositories(session).baselines
        await baselines.record(KIND_SOCIAL, term.key, NOW - timedelta(days=31), 99)
        await baselines.record(KIND_SOCIAL, removed.key, NOW - timedelta(hours=2), 20)
        await baselines.record("military_aircraft", "UA", NOW - timedelta(days=31), 99)
        await session.commit()
    await activity.record(NOW - timedelta(hours=3), {term.key: 0})
    await activity.record(NOW - timedelta(hours=2), {term.key: 4})
    await activity.record(NOW - timedelta(hours=2), {term.key: 2})
    await activity.record(NOW - timedelta(hours=1), {term.key: 40})
    rows = await activity.baselines(NOW - timedelta(days=30), NOW - timedelta(hours=1), [term.key])
    assert rows[term.key] == SocialBaseline(2, 2)
    assert await activity.baselines(NOW, NOW, []) == {}
    async with container.session_factory() as session:
        samples = list(await session.scalars(select(ActivitySampleRow)))
        assert len(samples) == 4
        assert any(row.kind == "military_aircraft" for row in samples)
    await activity.record(NOW, {})
    assert await activity.baselines(NOW - timedelta(days=30), NOW, [term.key]) == {}
    for invalid in [
        {"raw text": 1},
        {term.key: -1},
        {term.key: True},
        {f"{i:032x}": 1 for i in range(33)},
    ]:
        with pytest.raises(ValueError, match="Invalid social"):
            await activity.record(NOW, invalid)


async def test_sql_terms_read_enabled_plans(container: Container, user: User) -> None:
    async with container.session_factory() as session:
        await container.repositories(session).plans.add(social_plan(user.id, ["Secret"]))
        await session.commit()
    terms = await SqlSocialTerms(container.session_factory, ["ukraine"]).configured()
    assert len(terms) == 2 and terms[1].owners == frozenset({user.id})


async def test_social_board_api(client: AsyncClient, container: Container, user: User) -> None:
    assert (await client.get("/api/trackers/social")).status_code == 401
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    container.store.upsert([social_post("post", when=container.clock.now())])
    response = await client.get("/api/trackers/social", headers=bearer(token))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 1 and body["platforms"][0]["instance"] == "mastodon.social"
    assert body["hashtags"][0] == {"tag": "ukraine", "count": 1}
