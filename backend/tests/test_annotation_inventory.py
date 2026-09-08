"""Exact inventory additions, rapid corrections, overflow and historical replay."""

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select, update

from annotation_comparison_helpers import prepared
from annotation_monitor_helpers import correct
from ase.adapters.persistence.annotation_monitor_models import (
    AnnotationMonitorRow,
    AnnotationOutboxRow,
)
from ase.adapters.persistence.claims import SqlClaimRepository
from ase.application.reports.claims import ClaimInput
from ase.application.reports.comparison_inputs import ComparisonSelection
from ase.application.reports.monitor_history import retained_transition
from ase.domain.claim_revisions import ClaimCitationInput
from ase.domain.errors import InvalidRequest
from team_helpers import CONTEXT
from test_annotation_monitoring import tick


async def inventory_seed(client, container, user, *, empty=True, notify=True):
    actor, report, version, claim, _ = await prepared(client, container, user)
    async with container.session_factory() as session:
        if empty:
            await SqlClaimRepository(session).delete_for_report(report.id)
            await session.commit()
        monitor = await container.annotation_monitors(session).create(
            actor,
            "All annotations on this version",
            ComparisonSelection(report.id, 1),
            ("claim", "identity", "relationship"),
            notify,
            "report_inventory",
        )
    return actor, report, version, claim, monitor


async def add_claim(container, actor, report, template):
    value = ClaimInput(
        template.statement,
        template.kind,
        template.state,
        tuple(
            ClaimCitationInput(
                c.label, c.relation, c.excerpt.field, c.excerpt.start, c.excerpt.end, c.excerpt.text
            )
            for c in template.citations
        ),
        (),
        "Create another captured assertion.",
    )
    async with container.session_factory() as session:
        return await container.report_claims(session).create(actor, report.id, 1, value, CONTEXT)


@pytest.mark.parametrize("paused", [False, True])
async def test_empty_then_creation_and_rapid_corrections_preserve_exact_first_history(
    client, container, user, paused
):
    actor, report, _, template, monitor = await inventory_seed(client, container, user)
    assert monitor.watches == () and monitor.mode == "report_inventory"
    if paused:
        async with container.session_factory() as session:
            monitor = await container.annotation_monitors(session).update(
                actor, monitor.id, monitor.revision, "pause"
            )
    first = await add_claim(container, actor, report, template)
    second = await correct(container, actor, first)
    third = await correct(container, actor, second, reason="Further explanation.")
    if paused:
        assert not await tick(container, monitor.id)
        async with container.session_factory() as session:
            await container.annotation_monitors(session).update(
                actor, monitor.id, monitor.revision, "resume_catch_up"
            )
    for _ in range(3):
        assert await tick(container, monitor.id)
    async with container.session_factory() as session:
        service = container.annotation_monitors(session)
        rows, total = await service.repository.history(monitor.id, 20, 0)
        assert total == 3 and all(r.alert_id is not None for r in rows)
        initial, comparison, artifact = await retained_transition(
            service, actor, monitor.id, rows[-1].id
        )
        assert comparison.before.revisions == ()
        assert comparison.after.revisions == (first,)
        assert comparison.annotation_changes[0].status == "added"
    new_root = await add_claim(container, actor, report, template)
    assert await tick(container, monitor.id)
    async with container.session_factory() as session:
        service = container.annotation_monitors(session)
        assert (await service.get(actor, monitor.id)).watches[0].revision_id in {
            third.id,
            new_root.id,
        }
        assert (await retained_transition(service, actor, monitor.id, initial.id))[2] == artifact


async def test_missing_creation_is_gap_before_consuming_other_queued_event(client, container, user):
    actor, report, _, template, monitor = await inventory_seed(client, container, user)
    first = await add_claim(container, actor, report, template)
    await add_claim(container, actor, report, template)
    async with container.session_factory() as session:
        await session.execute(
            delete(AnnotationOutboxRow).where(AnnotationOutboxRow.revision_id == first.id)
        )
        await session.commit()
    assert not await tick(container, monitor.id)
    async with container.session_factory() as session:
        saved = await container.annotation_monitors(session).get(actor, monitor.id)
        assert saved.status == "unavailable" and saved.checkpoint_id == monitor.checkpoint_id
        assert "creation history is incomplete" in saved.unavailable_reason
        assert await session.scalar(select(func.count()).select_from(AnnotationOutboxRow)) == 1


async def test_twenty_first_creation_succeeds_without_partial_checkpoint_and_bounds_paused_queue(
    client, container, user
):
    actor, report, _, template, monitor = await inventory_seed(client, container, user)
    async with container.session_factory() as session:
        monitor = await container.annotation_monitors(session).update(
            actor, monitor.id, monitor.revision, "pause"
        )
    roots = [await add_claim(container, actor, report, template) for _ in range(21)]
    await correct(container, actor, roots[0])
    await add_claim(container, actor, report, template)
    async with container.session_factory() as session:
        service = container.annotation_monitors(session)
        assert (await session.get(AnnotationMonitorRow, monitor.id)).inventory_overflow
        assert await session.scalar(select(func.count()).select_from(AnnotationOutboxRow)) == 20
        assert await SqlClaimRepository(session).get(roots[-1].claim_id) is not None
        await service.update(actor, monitor.id, monitor.revision, "resume_catch_up")
    assert not await tick(container, monitor.id)
    async with container.session_factory() as session:
        service = container.annotation_monitors(session)
        saved = await service.get(actor, monitor.id)
        assert saved.status == "unavailable" and saved.checkpoint_id == monitor.checkpoint_id
        assert "Inventory capacity reached" in saved.unavailable_reason
        assert (await service.repository.history(monitor.id, 20, 0))[1] == 0
        with pytest.raises(InvalidRequest, match="twenty-root"):
            await service.create(
                actor,
                "Too many",
                ComparisonSelection(report.id, 1),
                ("claim",),
                True,
                "report_inventory",
            )


async def test_selected_never_discovers_and_inventory_rejects_client_selection(
    client, container, user
):
    actor, report, _, template, request = await prepared(client, container, user)
    async with container.session_factory() as session:
        service = container.annotation_monitors(session)
        monitor = await service.create(actor, "Selected", request.before, ("claim",), True)
        with pytest.raises(InvalidRequest, match="leave selections empty"):
            await service.create(actor, "All", request.before, ("claim",), True, "report_inventory")
    await add_claim(container, actor, report, template)
    assert not await tick(container, monitor.id)
    async with container.session_factory() as session:
        assert (
            await container.annotation_monitors(session).get(actor, monitor.id)
        ).watches == monitor.watches


async def test_forged_creation_revision_and_transaction_rollback_preserve_baseline(
    client, container, user
):
    actor, report, _, template, monitor = await inventory_seed(client, container, user)
    first = await add_claim(container, actor, report, template)
    second = await correct(container, actor, first)
    async with container.session_factory() as session:
        await session.execute(
            delete(AnnotationOutboxRow).where(AnnotationOutboxRow.revision_id == first.id)
        )
        await session.execute(update(AnnotationOutboxRow).values(previous_revision_id=None))
        await session.commit()
    assert not await tick(container, monitor.id)
    async with container.session_factory() as session:
        assert (
            await container.annotation_monitors(session).get(actor, monitor.id)
        ).checkpoint_id == monitor.checkpoint_id
        repo = SqlClaimRepository(session)
        await repo.create(replace(template, id=uuid4(), claim_id=uuid4()), "a" * 64)
        await session.rollback()
        assert await session.scalar(select(func.count()).select_from(AnnotationOutboxRow)) == 1
        assert second.number == 2
