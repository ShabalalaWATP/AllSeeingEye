"""A rule fires again only on new evidence, not on items its earlier alerts already cited."""

from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

from ase.adapters.persistence.warning import SqlWarningStore
from ase.adapters.persistence.warning_mapping import _alert_row
from ase.application.warning.indicators import IndicatorInput
from ase.domain.warning import Alert, Firing, Indicator, alert_from, evaluate
from assistant_helpers import event
from team_helpers import CONTEXT
from test_warning import NOW, indicator
from tracker_helpers import conflict_events


def test_domain_counts_only_items_not_already_alerted() -> None:
    events = {e.title: e for e in conflict_events(NOW)}
    shelling = replace(events["Shelling in Kharkiv"], published_at=NOW - timedelta(hours=1))
    later = replace(shelling, id="later", published_at=NOW - timedelta(minutes=5))
    rule = indicator(threshold=1)
    assert evaluate(rule, [shelling], NOW, None, frozenset({shelling.id})) is None
    firing = evaluate(rule, [shelling, later], NOW, None, frozenset({shelling.id}))
    assert firing is not None and firing.count == 1
    assert [item.id for item in firing.evidence] == ["later"]
    # Excluded items do not count towards the threshold either.
    twice = replace(rule, threshold=2)
    assert evaluate(twice, [shelling, later], NOW, None, frozenset({shelling.id})) is None


async def _rule(container, user):
    data = IndicatorInput("Quakes", threshold=2, window_minutes=360, cooldown_minutes=30)
    async with container.session_factory() as session:
        return await container.create_indicator(session).execute(user, data, CONTEXT)


def _quakes(clock, *names):
    return tuple(replace(event(name), published_at=clock.now()) for name in names)


async def test_rule_does_not_refire_on_already_alerted_items_after_the_cooldown(
    container, user, clock
):
    await _rule(container, user)
    evaluator = container.build_evaluator()
    container.store.upsert(_quakes(clock, "a", "b"))
    first = await evaluator.run_once()
    assert len(first) == 1 and set(first[0].event_ids) == {"a", "b"}

    clock.advance(timedelta(minutes=31))  # past the cooldown, items still inside the window
    assert await evaluator.run_once() == []

    container.store.upsert(_quakes(clock, "c"))
    assert await evaluator.run_once() == []  # one new item is below the threshold of two

    container.store.upsert(_quakes(clock, "d"))
    again = await evaluator.run_once()
    assert len(again) == 1 and set(again[0].event_ids) == {"c", "d"}
    assert again[0].count == 2


def alert(owner: Indicator, ids: list[str], fired_at) -> Alert:
    firing = Firing(len(ids), tuple(event(item) for item in ids), ())
    return alert_from(owner, firing, uuid4(), fired_at)


async def test_alerted_ids_are_filtered_by_rule_and_window_in_sql(container, user, clock):
    rule = await _rule(container, user)
    other = await _rule(container, user)
    store = SqlWarningStore(container.session_factory, container.access_policy)
    now = clock.now()

    old = alert(rule, ["old"], now - timedelta(hours=7))
    recent = alert(rule, ["x", "y"], now - timedelta(hours=1))
    foreign = alert(other, ["z"], now - timedelta(minutes=5))
    async with container.session_factory() as session:
        session.add_all([_alert_row(old), _alert_row(recent), _alert_row(foreign)])
        await session.commit()

    assert await store.alerted_event_ids(rule.id, now - rule.window) == frozenset({"x", "y"})
    assert await store.alerted_event_ids(other.id, now - other.window) == frozenset({"z"})
    assert await store.alerted_event_ids(uuid4(), now - rule.window) == frozenset()
