"""Explicit catch-up/reset semantics, unavailable recovery and bounded retention."""

import json

import pytest
from sqlalchemy import delete, func, select, update

from annotation_monitor_helpers import correct, seeded
from ase.adapters.persistence.annotation_monitor_models import (
    AnnotationMonitorRow,
    AnnotationOutboxRow,
    AnnotationTransitionRow,
)
from ase.adapters.persistence.models import UserRow
from ase.adapters.persistence.operational_models import AlertRow
from ase.application.reports import annotation_monitors
from ase.application.reports.monitor_history import retained_transition
from ase.domain.errors import Conflict, InvalidRequest, NotFound
from test_annotation_monitoring import tick


@pytest.mark.parametrize(
    "action,individual_alerts", [("resume_catch_up", 2), ("resume_rebaseline", 0)]
)
async def test_paused_corrections_require_explicit_catchup_or_retained_reset(
    client, container, user, action, individual_alerts
):
    actor, _, _, first, monitor = await seeded(client, container, user)
    async with container.session_factory() as session:
        paused = await container.annotation_monitors(session).update(actor, monitor.id, 1, "pause")
    second = await correct(container, actor, first)
    third = await correct(container, actor, second, reason="Additional analysis")
    assert not await tick(container, monitor.id)
    async with container.session_factory() as session:
        service = container.annotation_monitors(session)
        resumed = await service.update(actor, monitor.id, paused.revision, action)
        assert resumed.status == "active"
    for _ in range(3):
        await tick(container, monitor.id)
    async with container.session_factory() as session:
        service = container.annotation_monitors(session)
        rows, total = await service.repository.history(monitor.id, 20, 0)
        assert total == (2 if individual_alerts else 1)
        assert await session.scalar(select(func.count()).select_from(AlertRow)) == individual_alerts
        current = await service.get(actor, monitor.id)
        assert current.watches[0].revision_id == third.id
        assert rows[0].kind == ("revision" if individual_alerts else "rebaseline")


async def test_policy_change_requires_acknowledgement_and_freezes_new_policy(
    client, container, user
):
    actor, _, _, first, monitor = await seeded(client, container, user)
    await correct(container, actor, first)
    async with container.session_factory() as session:
        service = container.annotation_monitors(session)
        with pytest.raises(InvalidRequest, match="Confirm a fresh baseline"):
            await service.update(actor, monitor.id, 1, "configure", notify=False)
        assert await session.scalar(select(func.count()).select_from(AnnotationOutboxRow)) == 1
        changed = await service.update(
            actor, monitor.id, 1, "configure", notify=False, rebaseline_policy=True
        )
        assert changed.status == "active" and changed.checkpoint_number == 1
        rows, _ = await service.repository.history(monitor.id, 20, 0)
        assert rows[0].kind == "rebaseline" and rows[0].notify_on_change is False
        _, _, payload = await retained_transition(
            service, actor, monitor.id, rows[0].id, rows[0].comparison_sha256
        )
        artifact = json.loads(payload)
        assert artifact["transition"]["configuration_revision"] == changed.revision
        assert artifact["comparison"]["compared_by"] == str(user.id)
        assert await session.scalar(select(func.count()).select_from(AnnotationOutboxRow)) == 0
        assert await session.scalar(select(func.count()).select_from(AlertRow)) == 0


@pytest.mark.parametrize("fault", ["account", "gap", "payload", "quota"])
async def test_unavailable_observation_preserves_checkpoint_and_does_not_repeat_state_changes(
    client, container, user, monkeypatch, fault
):
    actor, _, _, first, monitor = await seeded(client, container, user)
    await correct(container, actor, first)
    async with container.session_factory() as session:
        if fault == "account":
            await session.execute(
                update(UserRow).where(UserRow.id == user.id).values(is_active=False)
            )
        elif fault == "gap":
            await session.execute(delete(AnnotationOutboxRow))
        elif fault == "payload":
            await session.execute(update(AnnotationMonitorRow).values(checkpoint_payload="{}"))
        else:
            monkeypatch.setattr(annotation_monitors, "MAX_MONITOR_GLOBAL_BYTES", 1)
        await session.commit()
    assert not await tick(container, monitor.id)
    assert not await tick(container, monitor.id)
    async with container.session_factory() as session:
        current = await container.annotation_monitors(session).repository.get(monitor.id)
        assert current.status == "unavailable" and current.checkpoint_id == monitor.checkpoint_id
        assert current.checkpoint_number == 0 and current.revision == 2
        assert await session.scalar(select(func.count()).select_from(AnnotationTransitionRow)) == 0
        assert await session.scalar(select(func.count()).select_from(AlertRow)) == 0
        if fault == "account":
            await session.execute(
                update(UserRow).where(UserRow.id == user.id).values(is_active=True)
            )
            await session.commit()
    if fault == "account":
        assert await tick(container, monitor.id)


async def test_delete_reclaims_only_target_history_alerts_and_queue(client, container, user):
    actor, report, _, first, monitor = await seeded(client, container, user)
    second = await correct(container, actor, first)
    assert await tick(container, monitor.id)
    await correct(container, actor, second)
    async with container.session_factory() as session:
        service = container.annotation_monitors(session)
        current = await service.get(actor, monitor.id)
        with pytest.raises(Conflict):
            await service.delete(actor, monitor.id, monitor.revision)
        await service.delete(actor, monitor.id, current.revision)
        for table in (AnnotationMonitorRow, AnnotationOutboxRow, AnnotationTransitionRow, AlertRow):
            assert await session.scalar(select(func.count()).select_from(table)) == 0
        assert await container.repositories(session).reports.get(report.id) is not None
        with pytest.raises(NotFound):
            await service.get(actor, monitor.id)


async def test_conflict_order_only_revision_is_retained_without_second_alert(
    client, container, user
):
    actor, _, _, first, monitor = await seeded(client, container, user)
    second = await correct(
        container, actor, first, conflicts=("First uncertainty", "Second uncertainty")
    )
    assert await tick(container, monitor.id)
    await correct(
        container,
        actor,
        second,
        state=second.state,
        reason=second.reason,
        conflicts=tuple(reversed(second.unresolved_conflicts)),
    )
    assert await tick(container, monitor.id)
    async with container.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(AnnotationTransitionRow)) == 2
        assert await session.scalar(select(func.count()).select_from(AlertRow)) == 1
