"""Consumption covers every counted match, independently of the citation sample."""

from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest

from ase.adapters.persistence.warning import SqlWarningStore
from ase.adapters.persistence.warning_consumption_models import WarningConsumptionRow
from ase.application.warning.evaluator import evaluate_candidates
from ase.application.warning.indicators import IndicatorInput
from ase.domain.consumed_evidence import digest
from ase.domain.warning import alert_from
from assistant_helpers import event
from team_helpers import CONTEXT
from test_indicator_ratios import seed_hours
from warning_scope_helpers import warning_actors as warning_actors  # noqa: PLC0414


async def create_rule(container, user, *, relative=False, **values):
    data = IndicatorInput(
        "Consumed evidence",
        threshold=2,
        cooldown_minutes=5,
        baseline_ratio=2 if relative else None,
        **values,
    )
    async with container.session_factory() as session:
        rule = await container.create_indicator(session).execute(user, data, CONTEXT)
    if relative:
        await seed_hours(container, rule, value=1)
    return rule


@pytest.mark.parametrize("relative", [False, True])
async def test_all_twenty_two_matches_stay_consumed_after_restart_and_cooldown(
    container,
    user,
    clock,
    relative,
):
    await create_rule(container, user, relative=relative)
    first_time = clock.now()
    container.store.upsert(
        [
            replace(event(str(index)), published_at=first_time - timedelta(seconds=index))
            for index in range(22)
        ]
    )
    first = await container.build_evaluator().run_once()
    assert len(first) == 1 and first[0].count == 22
    assert len(first[0].event_ids) == 20

    clock.advance(timedelta(minutes=6))
    restarted = container.build_evaluator()
    assert await restarted.run_once() == []

    # Publication predates the first alert. An event-time watermark would lose it.
    container.store.upsert(
        [
            replace(event("late-a"), published_at=first_time - timedelta(minutes=20)),
        ]
    )
    assert await restarted.run_once() == []
    container.store.upsert(
        [
            replace(event("late-b"), published_at=first_time - timedelta(minutes=20)),
        ]
    )
    second = await restarted.run_once()
    assert len(second) == 1
    assert second[0].count == (24 if relative else 2)
    if relative:
        assert second[0].baseline_mean == 1 and second[0].baseline_ratio == 24


async def test_consumption_survives_renames_matching_edits_and_longer_windows(
    container, user, clock
):
    rule = await create_rule(container, user, window_minutes=60)
    container.store.upsert([replace(event(str(i)), published_at=clock.now()) for i in range(22)])
    assert len(await container.build_evaluator().run_once()) == 1
    clock.advance(timedelta(hours=2))
    async with container.session_factory() as session:
        updated = await container.update_indicator(session).execute(
            user,
            rule.id,
            IndicatorInput(
                "Changed rule",
                countries=("JP",),
                keywords=("Earthquake",),
                threshold=2,
                cooldown_minutes=5,
                window_minutes=360,
            ),
            rule.updated_at,
            CONTEXT,
        )
    assert updated.updated_at != rule.updated_at
    assert await container.build_evaluator().run_once() == []


async def test_each_owner_and_team_consumes_its_own_evidence(container, warning_actors, clock):
    actors = warning_actors
    rules = [
        await create_rule(container, actors.owner),
        await create_rule(container, actors.owner, team_id=actors.team.id),
        await create_rule(container, actors.outsider, team_id=actors.other.id),
    ]
    items = [replace(event(str(i)), published_at=clock.now()) for i in range(22)]
    container.store.upsert(items)
    assert len(await container.build_evaluator().run_once()) == 3
    store = SqlWarningStore(container.session_factory, container.access_policy)
    for rule in rules:
        state = await store.consumed_evidence(rule, clock.now())
        assert state.identities == frozenset(digest(item) for item in items)
    forged = replace(rules[0], created_by=actors.outsider.id)
    assert (await store.consumed_evidence(forged, clock.now())).unavailable
    clock.advance(timedelta(minutes=6))
    assert await container.build_evaluator().run_once() == []
    async with container.session_factory() as session:
        await container.delete_indicator(session).execute(actors.owner, rules[0].id, CONTEXT)
    async with container.session_factory() as session:
        assert await session.get(WarningConsumptionRow, rules[0].id) is None
        assert await session.get(WarningConsumptionRow, rules[1].id) is not None


async def test_current_revision_fence_prevents_consumption_from_stale_work(container, user, clock):
    rule = await create_rule(container, user)
    container.store.upsert([replace(event(str(i)), published_at=clock.now()) for i in range(22)])
    firing = await evaluate_candidates(container.store, rule, clock.now(), None)
    assert firing is not None
    async with container.session_factory() as session:
        await container.update_indicator(session).execute(
            user,
            rule.id,
            IndicatorInput("Changed", threshold=2, cooldown_minutes=5),
            rule.updated_at,
            CONTEXT,
        )
    store = SqlWarningStore(container.session_factory, container.access_policy)
    assert not await store.add_alert(
        alert_from(rule, firing, uuid4(), clock.now()),
        rule,
        consumed=firing.consumed,
    )
    async with container.session_factory() as session:
        assert await session.get(WarningConsumptionRow, rule.id) is None
