"""Inventory recovery remains explicit; private or inconsistent roots cannot widen scope."""

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select, update

from ase.adapters.persistence.annotation_monitor_models import (
    AnnotationMonitorRow,
    AnnotationOutboxRow,
)
from ase.adapters.persistence.claim_models import ClaimRow
from ase.adapters.persistence.claims import SqlClaimRepository
from ase.application.reports.comparison_inputs import ComparisonSelection
from ase.application.reports.monitor_history import list_transitions, retained_transition
from ase.application.research.map_view_evidence import evidence_digest
from ase.domain.errors import Forbidden, NotFound
from helpers import USER_PASSWORD, bearer, login_token
from test_annotation_inventory import add_claim, inventory_seed
from test_annotation_monitoring import tick


async def test_pending_limit_preserves_history_until_explicit_baseline_and_reclaims_queue(
    client, container, user, monkeypatch
):
    actor, report, _, template, monitor = await inventory_seed(client, container, user)
    first = await add_claim(container, actor, report, template)
    assert await tick(container, monitor.id)
    async with container.session_factory() as session:
        service = container.annotation_monitors(session)
        metadata = (await service.repository.history(monitor.id, 20, 0))[0][0]
        original = (await retained_transition(service, actor, monitor.id, metadata.id))[2]
        valid = await service.get(actor, monitor.id)
    # Lower only this test's enqueue limit to exercise the same numerical boundary cheaply.
    monkeypatch.setattr("ase.adapters.persistence.annotation_outbox.MAX_MONITOR_PENDING_EVENTS", 2)
    roots = [await add_claim(container, actor, report, template) for _ in range(4)]
    assert not await tick(container, monitor.id)
    async with container.session_factory() as session:
        service = container.annotation_monitors(session)
        current = await service.get(actor, monitor.id)
        assert current.status == "unavailable" and "capacity" in current.unavailable_reason
        assert current.checkpoint_id == valid.checkpoint_id
        assert await session.scalar(select(func.count()).select_from(AnnotationOutboxRow)) == 2
        assert (await list_transitions(service, actor, monitor.id, 20, 0))[1] == 1
        assert (await retained_transition(service, actor, monitor.id, metadata.id))[2] == original
        resumed = await service.update(actor, monitor.id, current.revision, "resume_catch_up")
    assert not await tick(container, monitor.id)
    async with container.session_factory() as session:
        service = container.annotation_monitors(session)
        current = await service.get(actor, monitor.id)
        reset = await service.update(actor, monitor.id, current.revision, "resume_rebaseline")
        assert len(reset.watches) == 5
        assert {w.revision_id for w in reset.watches} == {first.id, *(r.id for r in roots)}
        assert not (await session.get(AnnotationMonitorRow, monitor.id)).inventory_overflow
        assert await session.scalar(select(func.count()).select_from(AnnotationOutboxRow)) == 0
        history, total = await service.repository.history(monitor.id, 20, 0)
        assert total == 2 and history[0].kind == "rebaseline" and history[0].alert_id is None
        assert (await retained_transition(service, actor, monitor.id, metadata.id))[2] == original
        assert resumed.checkpoint_id == valid.checkpoint_id
    assert not await tick(container, monitor.id)


async def test_gap_requires_explicit_reset_and_mode_is_immutable_in_http(client, container, user):
    actor, report, _, template, monitor = await inventory_seed(client, container, user)
    first = await add_claim(container, actor, report, template)
    async with container.session_factory() as session:
        await session.execute(delete(AnnotationOutboxRow))
        await session.commit()
    assert not await tick(container, monitor.id)
    async with container.session_factory() as session:
        service = container.annotation_monitors(session)
        current = await service.get(actor, monitor.id)
        assert "creation history is incomplete" in current.unavailable_reason
        reset = await service.update(actor, monitor.id, current.revision, "resume_rebaseline")
        assert reset.watches[0].revision_id == first.id
    response = await client.patch(
        f"/api/annotation-monitors/{monitor.id}",
        headers=bearer(await login_token(client, user.email, USER_PASSWORD)),
        json={"expected_revision": reset.revision, "action": "configure", "mode": "selected_roots"},
    )
    assert response.status_code == 422


async def test_wrong_scope_roots_filtered_before_inventory_cap_and_foreign_requests_denied(
    client, container, user, admin
):
    actor, report, version, template, monitor = await inventory_seed(client, container, user)
    async with container.session_factory() as session:
        repo = SqlClaimRepository(session)
        for _ in range(21):
            new = replace(template, id=uuid4(), claim_id=uuid4())
            await repo.create(new, evidence_digest(version))
            await session.execute(
                update(ClaimRow).where(ClaimRow.id == new.claim_id).values(created_by=admin.id)
            )
        # Deliberate inconsistent rows test scope filtering, not normal annotation creation.
        await session.execute(delete(AnnotationOutboxRow))
        await session.execute(update(AnnotationMonitorRow).values(inventory_overflow=False))
        await session.commit()
        service = container.annotation_monitors(session)
        assert await service.repository.inventory(monitor) == ()
        extra = await service.create(
            actor,
            "Authorised empty scope",
            ComparisonSelection(report.id, 1),
            ("identity",),
            False,
            "report_inventory",
        )
        assert extra.watches == ()
    assert not await tick(container, monitor.id)
    # Admin-owned personal report must remain private even though actor sees another report.
    foreign_actor, foreign_report, _, _, foreign = await inventory_seed(client, container, admin)
    async with container.session_factory() as session:
        service = container.annotation_monitors(session)
        with pytest.raises((Forbidden, NotFound)):
            await service.get(actor, foreign.id)
        with pytest.raises((Forbidden, NotFound)):
            await service.create(
                actor,
                "Foreign",
                ComparisonSelection(foreign_report.id, 1),
                ("claim",),
                False,
                "report_inventory",
            )
    assert foreign_actor.user_id == admin.id
