"""Real PostgreSQL monitoring races use guarded application mutations and separate connections."""

import asyncio
import os
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text, update
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from annotation_comparison_helpers import prepared
from annotation_monitor_helpers import correct, seeded
from ase.adapters.persistence.annotation_monitor_models import (
    AnnotationMonitorRow,
    AnnotationOutboxRow,
    AnnotationTransitionRow,
    AnnotationWatchRow,
)
from ase.adapters.persistence.claim_models import ClaimRow
from ase.adapters.persistence.models import AlertRow, ReportRow
from ase.adapters.persistence.users import SqlUserRepository
from ase.application.reports.monitor_history import retained_transition
from ase.application.reports.monitor_observation import observe
from ase.domain.errors import Conflict, NotFound
from team_helpers import CONTEXT, team_service
from test_report_team_scope import team_for


@pytest.fixture
async def settings(settings):
    source = os.environ.get("ASE_MONITOR_CONCURRENCY_POSTGRES_URL")
    if not source:
        pytest.skip("Set ASE_MONITOR_CONCURRENCY_POSTGRES_URL to a disposable PG server")
    url = make_url(source)
    assert url.drivername == "postgresql+asyncpg"
    assert url.host in {"127.0.0.1", "localhost", "::1"}
    name = f"ase_monitor_race_{uuid4().hex}"
    admin = create_async_engine(url, isolation_level="AUTOCOMMIT")
    try:
        async with admin.connect() as connection:
            await connection.execute(text(f'CREATE DATABASE "{name}"'))
        try:
            yield settings.model_copy(
                update={
                    "database_url": url.set(database=name).render_as_string(hide_password=False)
                }
            )
        finally:
            async with admin.connect() as connection:
                await connection.execute(text(f'DROP DATABASE "{name}"'))
    finally:
        await admin.dispose()


async def race(container, monkeypatch, holder, waiter):
    """Keep the first real guard held until PostgreSQL reports the other writer waiting."""
    held, waiting, release = asyncio.Event(), asyncio.Event(), asyncio.Event()
    pids = {}
    original = SqlUserRepository.lock_administration

    async def lock(repository):
        task = asyncio.current_task()
        name = task.get_name() if task else ""
        if name not in {"monitor-holder", "monitor-waiter"} or name in pids:
            return await original(repository)
        pids[name] = await repository._session.scalar(text("SELECT pg_backend_pid()"))
        if name == "monitor-waiter":
            waiting.set()
        await original(repository)
        if name == "monitor-holder":
            held.set()
            await asyncio.wait_for(release.wait(), 15)

    tasks = []
    with monkeypatch.context() as patch:
        patch.setattr(SqlUserRepository, "lock_administration", lock)
        try:
            tasks.append(asyncio.create_task(holder(), name="monitor-holder"))
            await asyncio.wait_for(held.wait(), 10)
            tasks.append(asyncio.create_task(waiter(), name="monitor-waiter"))
            await asyncio.wait_for(waiting.wait(), 10)
            async with asyncio.timeout(5), container.session_factory() as session:
                while True:
                    blocked = await session.scalar(
                        text("SELECT wait_event_type FROM pg_stat_activity WHERE pid = :pid"),
                        {"pid": pids["monitor-waiter"]},
                    )
                    if blocked == "Lock":
                        break
                    await session.rollback()
                    await asyncio.sleep(0.01)
            assert len(set(pids.values())) == 2, "Race requires independent PostgreSQL connections"
            assert not tasks[1].done()
            release.set()
            async with asyncio.timeout(20):
                return await asyncio.gather(*tasks, return_exceptions=True)
        finally:
            release.set()
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)


async def observe_once(container, key):
    async with container.session_factory() as session:
        return await observe(container.annotation_monitors(session), key)


async def monitor_state(container, key):
    async with container.session_factory() as session:
        repository = container.annotation_monitors(session).repository
        return await repository.get(key), await repository.history(key, 50, 0)


async def counts(container):
    async with container.session_factory() as session:
        return tuple(
            [
                await session.scalar(select(func.count()).select_from(model))
                for model in (
                    AnnotationMonitorRow,
                    AnnotationWatchRow,
                    AnnotationOutboxRow,
                    AnnotationTransitionRow,
                    AlertRow,
                )
            ]
        )


async def test_two_workers_commit_one_exact_transition_and_alert(
    client, container, user, monkeypatch
):
    actor, _, _, first, monitor = await seeded(client, container, user)
    second = await correct(container, actor, first)
    results = await race(
        container,
        monkeypatch,
        lambda: observe_once(container, monitor.id),
        lambda: observe_once(container, monitor.id),
    )
    assert results == [True, False]
    current, (history, total) = await monitor_state(container, monitor.id)
    assert total == current.checkpoint_number == 1
    assert current.watches[0].revision_id == second.id
    assert await counts(container) == (1, 1, 0, 1, 1)
    async with container.session_factory() as session:
        metadata, comparison, _ = await retained_transition(
            container.annotation_monitors(session), actor, monitor.id, history[0].id
        )
        assert comparison.before.revisions[0] == first
        assert comparison.after.revisions[0] == second
        assert metadata.checkpoint_before == monitor.checkpoint_id
        alert = (await session.scalars(select(AlertRow))).one()
        assert alert.annotation_transition_id == metadata.id


@pytest.mark.parametrize("baseline_first", [True, False])
async def test_append_and_baseline_order_preserves_exact_revision(
    client, container, user, monkeypatch, baseline_first
):
    actor, _, _, first, request = await prepared(client, container, user)

    async def baseline():
        async with container.session_factory() as session:
            return await container.annotation_monitors(session).create(
                actor, "Exact baseline", request.before, ("claim",), True
            )

    async def append():
        return await correct(container, actor, first)

    results = await race(
        container,
        monkeypatch,
        baseline if baseline_first else append,
        append if baseline_first else baseline,
    )
    if not baseline_first:
        assert not isinstance(results[0], BaseException)
        assert isinstance(results[1], Conflict)
        assert await counts(container) == (0, 0, 0, 0, 0)
        return
    monitor, correction = results
    assert monitor.watches[0].revision_id == first.id
    assert await counts(container) == (1, 1, 1, 0, 0)
    assert await observe_once(container, monitor.id)
    current, _ = await monitor_state(container, monitor.id)
    assert current.watches[0].revision_id == correction.id
    assert await counts(container) == (1, 1, 0, 1, 1)


async def test_membership_revocation_wins_before_observation_without_advancing_baseline(
    client, container, admin, user, monkeypatch
):
    team = await team_for(container, admin, user)
    actor, report, _, first, request = await prepared(client, container, user)
    # Fixture setup only; the raced revocation below uses the real TeamService.
    async with container.session_factory() as session:
        await session.execute(
            update(ReportRow).where(ReportRow.id == report.id).values(team_id=team.id)
        )
        await session.execute(
            update(ClaimRow).where(ClaimRow.report_id == report.id).values(team_id=team.id)
        )
        await session.commit()
        monitor = await container.annotation_monitors(session).create(
            actor, "Team watch", request.before, ("claim",), True
        )
    await correct(container, actor, first)

    async def revoke():
        async with team_service(container) as service:
            await service.remove_member(admin, team.id, user.id, CONTEXT)

    assert await race(
        container, monkeypatch, revoke, lambda: observe_once(container, monitor.id)
    ) == [None, False]
    current, (_, total) = await monitor_state(container, monitor.id)
    assert current.status == "unavailable" and total == 0
    assert current.checkpoint_id == monitor.checkpoint_id and current.watches == monitor.watches
    assert await counts(container) == (1, 1, 1, 0, 0)


@pytest.mark.parametrize("target", ["parent", "monitor"])
@pytest.mark.parametrize("operation", ["observe", "export"])
async def test_deletion_committed_before_observation_or_export_prevents_delivery(
    client, container, user, monkeypatch, target, operation
):
    actor, report, _, first, monitor = await seeded(client, container, user)
    await correct(container, actor, first)
    transition = None
    if operation == "export":
        assert await observe_once(container, monitor.id)
        monitor, (history, _) = await monitor_state(container, monitor.id)
        transition = history[0]

    async def remove():
        async with container.session_factory() as session:
            if target == "parent":
                await container.delete_report(session).execute(user, report.id, CONTEXT)
            else:
                await container.annotation_monitors(session).delete(
                    actor, monitor.id, monitor.revision
                )

    async def read():
        if operation == "observe":
            return await observe_once(container, monitor.id)
        async with container.session_factory() as session:
            return await retained_transition(
                container.annotation_monitors(session), actor, monitor.id, transition.id
            )

    results = await race(container, monkeypatch, remove, read)
    assert results[0] is None
    assert results[1] is False if operation == "observe" else isinstance(results[1], NotFound)
    assert await counts(container) == (0, 0, 0, 0, 0)


@pytest.mark.parametrize("target", ["parent", "monitor"])
async def test_export_guard_holds_exact_transition_until_authorised_deletion_can_commit(
    client, container, user, monkeypatch, target
):
    actor, report, _, first, monitor = await seeded(client, container, user)
    second = await correct(container, actor, first)
    assert await observe_once(container, monitor.id)
    monitor, (history, _) = await monitor_state(container, monitor.id)
    transition = history[0]

    async def export():
        async with container.session_factory() as session:
            return await retained_transition(
                container.annotation_monitors(session),
                actor,
                monitor.id,
                transition.id,
                transition.comparison_sha256,
            )

    async def remove():
        async with container.session_factory() as session:
            if target == "parent":
                await container.delete_report(session).execute(user, report.id, CONTEXT)
            else:
                await container.annotation_monitors(session).delete(
                    actor, monitor.id, monitor.revision
                )

    results = await race(container, monkeypatch, export, remove)
    metadata, comparison, content = results[0]
    assert results[1] is None and content and metadata == transition
    assert comparison.before.revisions[0] == first and comparison.after.revisions[0] == second
    assert await counts(container) == (0, 0, 0, 0, 0)
