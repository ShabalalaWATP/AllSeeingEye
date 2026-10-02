"""A shared first acknowledgement contributes once to its scoped UTC daily split."""

from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from ase.adapters.persistence.alert_feedback import AlertFeedbackRow
from ase.adapters.persistence.warning import SqlWarningStore
from ase.adapters.persistence.warning_mapping import _alert_row
from ase.domain.alert_feedback import AlertDisposition
from ase.domain.errors import Forbidden, InvalidRequest, NotFound
from ase.domain.warning import Alert
from team_helpers import CONTEXT, team_service
from warning_scope_helpers import create_indicator
from warning_scope_helpers import warning_actors as warning_actors  # noqa: PLC0414


async def seed(container, user, team_id=None, *, rule_notification=True):
    rule = await create_indicator(container, user, team_id)
    alert = Alert(
        uuid4(),
        rule.id,
        container.clock.now(),
        "Synthetic alert",
        "",
        4,
        1,
        (),
        (),
        created_by=user.id,
        team_id=team_id,
    )
    if not rule_notification:
        alert = replace(alert, indicator_id=None, schedule_id=uuid4())
    async with container.session_factory() as session:
        session.add(_alert_row(alert))
        await session.commit()
    return rule, alert


async def acknowledge(container, actor, alert, disposition=None, note=None):
    async with container.session_factory() as session:
        return await container.acknowledge_alert(session).execute(
            actor,
            alert.id,
            CONTEXT,
            disposition=disposition,
            note=note,
        )


async def feedback(container, actor, rule):
    async with container.session_factory() as session:
        return await container.alert_feedback(session).execute(actor, rule.id)


async def test_optional_acknowledgement_and_first_disposition_are_immutable(container, user):
    rule, alert = await seed(container, user)
    first = await acknowledge(container, user, alert, AlertDisposition.USEFUL, "Relevant")
    retry = await acknowledge(container, user, alert, AlertDisposition.NOISE, "Replace")
    assert retry == first
    assert retry.disposition is AlertDisposition.USEFUL and retry.disposition_note == "Relevant"
    counts = await feedback(container, user, rule)
    assert (counts.useful, counts.noise, counts.duplicate) == (1, 0, 0)
    rule2, alert2 = await seed(container, user)
    plain = await acknowledge(container, user, alert2)
    assert plain.disposition is None
    assert (await feedback(container, user, rule2)).useful == 0


async def test_atomic_compare_and_set_rejects_competing_stale_write(container, user):
    rule, alert = await seed(container, user)
    first = await acknowledge(container, user, alert, AlertDisposition.USEFUL)
    async with container.session_factory() as session:
        repos = container.repositories(session)
        assert not await repos.alerts.acknowledge(
            replace(first, disposition=AlertDisposition.NOISE)
        )
        await repos.uow.commit()
    assert (await feedback(container, user, rule)).noise == 0


async def test_shared_team_decision_checks_current_write_scope(container, admin, warning_actors):
    actors = warning_actors
    rule, alert = await seed(container, actors.owner, actors.team.id)
    first = await acknowledge(container, actors.peer, alert, AlertDisposition.DUPLICATE)
    assert first.acknowledged_by == actors.peer.id
    assert await acknowledge(container, actors.owner, alert, AlertDisposition.NOISE) == first
    with pytest.raises(NotFound):
        await feedback(container, actors.outsider, rule)
    async with team_service(container) as service:
        await service.update(admin, actors.team.id, name=None, is_active=False, context=CONTEXT)
    with pytest.raises(Forbidden):
        await acknowledge(container, actors.peer, alert)
    assert (await feedback(container, actors.peer, rule)).duplicate == 1
    async with team_service(container) as service:
        await service.update(admin, actors.team.id, name=None, is_active=True, context=CONTEXT)
        await service.remove_member(admin, actors.team.id, actors.peer.id, CONTEXT)
    with pytest.raises(NotFound):
        await acknowledge(container, actors.peer, alert)


async def test_acknowledgement_window_survives_raw_pruning_then_expires(container, user):
    rule, alert = await seed(container, user)
    container.clock.advance(timedelta(days=29))
    await acknowledge(container, user, alert, AlertDisposition.NOISE)
    container.clock.advance(timedelta(days=2))
    store = SqlWarningStore(container.session_factory, container.access_policy)
    assert await store.prune(container.clock.now() - timedelta(days=30)) == 1
    counts = await feedback(container, user, rule)
    assert counts.noise == 1 and "acknowledgement day" in counts.time_basis
    container.clock.advance(timedelta(days=28))
    await store.prune(container.clock.now() - timedelta(days=30))
    assert (await feedback(container, user, rule)).noise == 0
    async with container.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(AlertFeedbackRow)) == 0


async def test_non_rule_notifications_and_deleted_rules_do_not_leak_counts(container, user):
    rule, alert = await seed(container, user, rule_notification=False)
    await acknowledge(container, user, alert, AlertDisposition.NOISE)
    assert (await feedback(container, user, rule)).noise == 0
    async with container.session_factory() as session:
        await container.delete_indicator(session).execute(user, rule.id, CONTEXT)
    with pytest.raises(NotFound):
        await feedback(container, user, rule)


@pytest.mark.parametrize("note", ["x" * 201, "hidden\x00text"])
async def test_notes_are_bounded_plain_text(container, user, note):
    _, alert = await seed(container, user)
    with pytest.raises(InvalidRequest):
        await acknowledge(container, user, alert, note=note)
