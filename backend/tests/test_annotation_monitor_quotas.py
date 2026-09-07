"""Monitor quotas stop work before creating manifests and never erase another baseline."""

import pytest
from sqlalchemy import func, select

from annotation_comparison_helpers import prepared
from annotation_monitor_helpers import correct, seeded
from ase.adapters.persistence.annotation_monitor_models import (
    AnnotationMonitorRow,
    AnnotationOutboxRow,
    AnnotationTransitionRow,
)
from ase.application.reports import annotation_monitors, monitor_observation
from ase.domain.errors import InvalidRequest
from test_annotation_monitoring import tick


@pytest.mark.parametrize(
    "limit",
    [
        "MAX_MONITORS_PER_SCOPE",
        "MAX_MONITORS_GLOBAL",
        "MAX_MONITOR_BYTES",
        "MAX_MONITOR_GLOBAL_BYTES",
    ],
)
async def test_creation_caps_precede_manifest_work(client, container, user, monkeypatch, limit):
    actor, _, _, _, request = await prepared(client, container, user)
    monkeypatch.setattr(annotation_monitors, limit, 0)

    def forbidden(*args):
        pytest.fail("Capacity must be checked before serialising a new baseline")

    monkeypatch.setattr(annotation_monitors, "build_observation", forbidden)
    async with container.session_factory() as session:
        with pytest.raises(InvalidRequest, match="storage limit"):
            await container.annotation_monitors(session).create(
                actor, "Bounded", request.before, ("claim",), True
            )
        assert await session.scalar(select(func.count()).select_from(AnnotationMonitorRow)) == 0


async def test_transition_cap_preserves_queued_revision_before_serialisation(
    client, container, user, monkeypatch
):
    actor, _, _, first, monitor = await seeded(client, container, user)
    await correct(container, actor, first)
    monkeypatch.setattr(monitor_observation, "MAX_TRANSITIONS", 0)

    def forbidden(*args):
        pytest.fail("Transition capacity must precede new comparison serialisation")

    monkeypatch.setattr(monitor_observation, "build_observation", forbidden)
    assert not await tick(container, monitor.id)
    async with container.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(AnnotationTransitionRow)) == 0
        assert await session.scalar(select(func.count()).select_from(AnnotationOutboxRow)) == 1
        current = await container.annotation_monitors(session).repository.get(monitor.id)
        assert current.checkpoint_id == monitor.checkpoint_id and current.status == "unavailable"


async def test_monitor_deletion_preserves_other_subscription_and_reclaims_only_own_bytes(
    client, container, user
):
    actor, report, _, first, request = await prepared(client, container, user)
    async with container.session_factory() as session:
        service = container.annotation_monitors(session)
        one = await service.create(actor, "One", request.before, ("claim",), True)
        two = await service.create(actor, "Two", request.before, ("claim",), True)
    await correct(container, actor, first)
    assert await tick(container, one.id)
    assert await tick(container, two.id)
    async with container.session_factory() as session:
        service = container.annotation_monitors(session)
        before = await service.repository.usage(user.id, None)
        current = await service.get(actor, one.id)
        await service.delete(actor, one.id, current.revision)
        after = await service.repository.usage(user.id, None)
        assert after[0] == 1 and after[2] < before[2] and after[3] < before[3]
        assert (await service.get(actor, two.id)).checkpoint_number == 1
        assert (await service.repository.history(two.id, 20, 0))[1] == 1
        assert await container.repositories(session).reports.get(report.id) is not None
