"""Every watched revision survives rapid reversals, restart, replay and opt-out."""

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from annotation_monitor_helpers import correct, seeded
from ase.adapters.persistence.annotation_monitor_models import (
    AnnotationOutboxRow,
    AnnotationTransitionRow,
)
from ase.adapters.persistence.claims import SqlClaimRepository
from ase.adapters.persistence.operational_models import AlertRow
from ase.application.reports.monitor_history import retained_transition
from ase.application.reports.monitor_observation import observe
from ase.domain.claim_revisions import ClaimReviewState
from ase.domain.errors import Conflict


async def tick(container, key):
    async with container.session_factory() as session:
        return await observe(container.annotation_monitors(session), key)


async def test_initial_baseline_then_rapid_reversal_retains_both_intermediate_transitions(
    client, container, user
):
    actor, _, _, first, monitor = await seeded(client, container, user)
    assert not await tick(container, monitor.id)
    second = await correct(container, actor, first)
    third = await correct(
        container, actor, second, state=ClaimReviewState.PROPOSED, reason=first.reason
    )
    assert await tick(container, monitor.id)
    assert await tick(container, monitor.id)
    assert not await tick(container, monitor.id)
    async with container.session_factory() as session:
        service = container.annotation_monitors(session)
        current = await service.get(actor, monitor.id)
        rows, total = await service.repository.history(monitor.id, 20, 0)
        assert total == 2 and current.checkpoint_number == 2
        assert current.watches[0].revision_id == third.id
        _, one, _ = await retained_transition(service, actor, monitor.id, rows[1].id)
        _, two, _ = await retained_transition(service, actor, monitor.id, rows[0].id)
        assert (one.before.revisions[0].id, one.after.revisions[0].id) == (first.id, second.id)
        assert (two.before.revisions[0].id, two.after.revisions[0].id) == (second.id, third.id)
        alerts = list(await session.scalars(select(AlertRow)))
        assert len(alerts) == 2
        assert all(
            a.annotation_monitor_id == monitor.id
            and a.schedule_id is None
            and a.indicator_id is None
            for a in alerts
        )
        assert all(not a.event_ids and first.statement not in a.summary for a in alerts)


async def test_rolled_back_revision_does_not_leave_an_outbox_delivery(client, container, user):
    _, _, _, first, monitor = await seeded(client, container, user)
    value = replace(first, id=uuid4(), number=2, previous_id=first.id, reason="Rolled back")
    async with container.session_factory() as session:
        assert await SqlClaimRepository(session).append(value, first.id)
        assert await session.scalar(select(func.count()).select_from(AnnotationOutboxRow)) == 1
        await session.rollback()
    assert not await tick(container, monitor.id)
    async with container.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(AnnotationOutboxRow)) == 0


@pytest.mark.parametrize("notify", [False, True])
async def test_rationale_only_is_substantive_but_identical_metadata_revision_is_quiet(
    client, container, user, notify
):
    actor, _, _, first, monitor = await seeded(client, container, user, notify=notify)
    second = await correct(
        container, actor, first, state=first.state, reason="Explanation corrected substantively."
    )
    assert await tick(container, monitor.id)
    await correct(container, actor, second, state=second.state, reason=second.reason)
    assert await tick(container, monitor.id)
    async with container.session_factory() as session:
        rows = list(
            await session.scalars(
                select(AnnotationTransitionRow).order_by(AnnotationTransitionRow.sequence)
            )
        )
        assert rows[0].changed_categories == ["claim"] and rows[1].changed_categories == []
        assert await session.scalar(select(func.count()).select_from(AlertRow)) == int(notify)


async def test_stale_checkpoint_cas_cannot_append_transition_or_alert(client, container, user):
    actor, _, _, first, monitor = await seeded(client, container, user)
    await correct(container, actor, first)
    assert await tick(container, monitor.id)
    async with container.session_factory() as session:
        service = container.annotation_monitors(session)
        with pytest.raises(Conflict):
            await service.update(actor, monitor.id, monitor.revision, "pause")
        assert await session.scalar(select(func.count()).select_from(AnnotationTransitionRow)) == 1
