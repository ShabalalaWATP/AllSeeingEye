"""Inventory admission and event delivery contend through real PostgreSQL application guards."""

import pytest
from sqlalchemy import select

from annotation_monitor_helpers import correct
from ase.adapters.persistence.annotation_monitor_models import (
    AnnotationMonitorRow,
    AnnotationOutboxRow,
)
from ase.adapters.persistence.claim_models import ClaimRow
from ase.application.reports.comparison_inputs import ComparisonSelection
from report_documents_helpers import document_records
from team_helpers import CONTEXT, team_service
from test_annotation_monitoring_concurrency_postgres import (
    counts,
    monitor_state,
    observe_once,
    race,
)
from test_annotation_monitoring_concurrency_postgres import (
    settings as settings,  # noqa: PLC0414
)
from test_report_claim_service import value_for
from test_report_team_scope import team_for
from test_saved_map_views import claims_for


async def empty_report(client, container, user, team=None):
    actor = await claims_for(client, container, user)
    report, version = document_records(user.id)
    report.team_id = team.id if team else None
    async with container.session_factory() as session:
        await container.repositories(session).reports.add(report, version)
        await session.commit()
    return actor, report, version


async def inventory(container, actor, report):
    async with container.session_factory() as session:
        return await container.annotation_monitors(session).create(
            actor,
            "Full saved-version inventory",
            ComparisonSelection(report.id, 1),
            ("claim", "identity", "relationship"),
            True,
            mode="report_inventory",
        )


async def create_claim(container, actor, report, version):
    async with container.session_factory() as session:
        return await container.report_claims(session).create(
            actor,
            report.id,
            1,
            value_for(version),
            CONTEXT,
        )


@pytest.mark.parametrize("admission_first", [True, False])
async def test_empty_admission_and_creation_have_exact_ordered_baselines(
    client, container, user, monkeypatch, admission_first
):
    actor, report, version = await empty_report(client, container, user)

    async def admit():
        return await inventory(container, actor, report)

    async def create():
        return await create_claim(container, actor, report, version)

    results = await race(
        container,
        monkeypatch,
        admit if admission_first else create,
        create if admission_first else admit,
    )
    monitor, claim = results if admission_first else results[::-1]
    assert monitor.mode == "report_inventory"
    if admission_first:
        assert monitor.watches == ()
        assert await counts(container) == (1, 0, 1, 0, 0)
        assert await observe_once(container, monitor.id)
        current, _ = await monitor_state(container, monitor.id)
        assert current.watches[0].revision_id == claim.id
    else:
        assert monitor.watches[0].revision_id == claim.id
        assert not await observe_once(container, monitor.id)
        assert await counts(container) == (1, 1, 0, 0, 0)


async def test_creation_and_append_before_two_observers_preserve_each_revision(
    client, container, user, monkeypatch
):
    actor, report, version = await empty_report(client, container, user)
    monitor = await inventory(container, actor, report)
    first = await create_claim(container, actor, report, version)
    second = await correct(container, actor, first)
    async with container.session_factory() as session:
        events = list(
            await session.scalars(select(AnnotationOutboxRow).order_by(AnnotationOutboxRow.id))
        )
        assert [(row.previous_revision_id, row.revision_id) for row in events] == [
            (None, first.id),
            (first.id, second.id),
        ]
    results = await race(
        container,
        monkeypatch,
        lambda: observe_once(container, monitor.id),
        lambda: observe_once(container, monitor.id),
    )
    assert results == [True, True]
    current, (history, total) = await monitor_state(container, monitor.id)
    assert total == 2 and current.watches[0].revision_id == second.id
    assert len({row.id for row in history}) == 2
    assert await counts(container) == (1, 1, 0, 2, 2)
    assert await race(
        container,
        monkeypatch,
        lambda: observe_once(container, monitor.id),
        lambda: observe_once(container, monitor.id),
    ) == [False, False]


async def test_competing_observers_deliver_single_creation_once(
    client, container, user, monkeypatch
):
    actor, report, version = await empty_report(client, container, user)
    monitor = await inventory(container, actor, report)
    await create_claim(container, actor, report, version)
    assert await race(
        container,
        monkeypatch,
        lambda: observe_once(container, monitor.id),
        lambda: observe_once(container, monitor.id),
    ) == [True, False]
    assert await counts(container) == (1, 1, 0, 1, 1)


async def test_twenty_first_creation_succeeds_and_preserves_complete_checkpoint(
    client, container, user, monkeypatch
):
    actor, report, version = await empty_report(client, container, user)
    for _ in range(20):
        await create_claim(container, actor, report, version)
    monitor = await inventory(container, actor, report)
    results = await race(
        container,
        monkeypatch,
        lambda: create_claim(container, actor, report, version),
        lambda: observe_once(container, monitor.id),
    )
    assert not isinstance(results[0], BaseException) and results[1] is False
    current, (_, total) = await monitor_state(container, monitor.id)
    assert current.status == "unavailable" and current.checkpoint_id == monitor.checkpoint_id
    assert current.watches == monitor.watches and total == 0
    async with container.session_factory() as session:
        assert await session.scalar(select(AnnotationMonitorRow.inventory_overflow)) is True
        assert len(list(await session.scalars(select(ClaimRow)))) == 21
    assert await counts(container) == (1, 20, 0, 0, 0)


async def test_revocation_before_creation_observation_preserves_empty_baseline(
    client, container, admin, user, monkeypatch
):
    team = await team_for(container, admin, user)
    actor, report, version = await empty_report(client, container, user, team)
    monitor = await inventory(container, actor, report)
    await create_claim(container, actor, report, version)

    async def revoke():
        async with team_service(container) as service:
            await service.remove_member(admin, team.id, user.id, CONTEXT)

    assert await race(
        container, monkeypatch, revoke, lambda: observe_once(container, monitor.id)
    ) == [None, False]
    current, (_, total) = await monitor_state(container, monitor.id)
    assert current.status == "unavailable" and current.checkpoint_id == monitor.checkpoint_id
    assert current.watches == () and total == 0
    assert await counts(container) == (1, 0, 1, 0, 0)


@pytest.mark.parametrize("target", ["parent", "monitor"])
async def test_guarded_deletion_before_inventory_observation_removes_pending_delivery(
    client, container, user, monkeypatch, target
):
    actor, report, version = await empty_report(client, container, user)
    monitor = await inventory(container, actor, report)
    await create_claim(container, actor, report, version)

    async def remove():
        async with container.session_factory() as session:
            if target == "parent":
                await container.delete_report(session).execute(user, report.id, CONTEXT)
            else:
                await container.annotation_monitors(session).delete(
                    actor, monitor.id, monitor.revision
                )

    assert await race(
        container, monkeypatch, remove, lambda: observe_once(container, monitor.id)
    ) == [None, False]
    assert await counts(container) == (0, 0, 0, 0, 0)
