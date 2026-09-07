"""Independent PostgreSQL proof of the final dual-parent comparison authority guard."""

import asyncio
import os
from dataclasses import replace
from threading import Event
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from annotation_comparison_helpers import prepared
from ase.adapters.persistence.users import SqlUserRepository
from ase.application.reports import annotation_comparisons
from ase.application.reports.claim_export_selection import ClaimExportReference
from ase.application.reports.comparison_inputs import ComparisonSelection
from ase.application.reports.comparison_manifest import comparison_json
from ase.domain.errors import NotFound
from team_helpers import CONTEXT
from test_claim_repository import seed


@pytest.fixture
async def settings(settings):
    source = os.environ.get("ASE_COMPARISON_CONCURRENCY_POSTGRES_URL")
    if not source:
        pytest.skip("Set ASE_COMPARISON_CONCURRENCY_POSTGRES_URL to a disposable PG server")
    url = make_url(source)
    assert url.drivername == "postgresql+asyncpg"
    assert url.host in {"127.0.0.1", "localhost", "::1"}
    name = f"ase_comparison_race_{uuid4().hex}"
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


async def two_reports(client, container, user):
    actor, first, _, _, request = await prepared(client, container, user)
    second, _, revision = await seed(container, user)
    return (
        actor,
        first,
        second,
        replace(
            request,
            after=ComparisonSelection(
                second.id, 1, (ClaimExportReference(revision.claim_id, revision.id),)
            ),
        ),
    )


async def delete_report(container, user, report_id):
    # Exercise the real authorised mutation, including its shared guard and audit commit.
    async with container.session_factory() as session:
        await container.delete_report(session).execute(user, report_id, CONTEXT)


async def observe_database_lock(container, pid):
    async with asyncio.timeout(5), container.session_factory() as session:
        while True:
            state = await session.scalar(
                text("SELECT wait_event_type FROM pg_stat_activity WHERE pid = :pid"), {"pid": pid}
            )
            if state == "Lock":
                return
            await session.rollback()
            await asyncio.sleep(0.01)


@pytest.mark.parametrize("export", [False, True], ids=["preview", "export"])
async def test_authorised_first_parent_deletion_waits_through_both_final_checks(
    client, container, user, monkeypatch, export
):
    actor, first, second, request = await two_reports(client, container, user)
    first_checked, release, delete_waiting = asyncio.Event(), asyncio.Event(), asyncio.Event()
    final_phase = False
    checked, pids = [], {}
    original_release = annotation_comparisons.recheck_comparison
    original_lock = SqlUserRepository.lock_administration

    async def guarded_release(*args):
        nonlocal final_phase
        final_phase = True
        return await original_release(*args)

    async def lock(repository):
        task = asyncio.current_task()
        if task and task.get_name() == "comparison-delete":
            pids["delete"] = await repository._session.scalar(text("SELECT pg_backend_pid()"))
            delete_waiting.set()
        await original_lock(repository)

    async with container.session_factory() as session:
        service = container.annotation_comparisons(session)
        preview = await service.execute(actor, request)
        original_report = service.selector.claims._report

        async def report(access, report_id):
            record = await original_report(access, report_id)
            if final_phase:
                checked.append(report_id)
                if len(checked) == 1:
                    assert report_id == first.id
                    pids["comparison"] = await session.scalar(text("SELECT pg_backend_pid()"))
                    first_checked.set()
                    await asyncio.wait_for(release.wait(), 10)
            return record

        monkeypatch.setattr(annotation_comparisons, "recheck_comparison", guarded_release)
        monkeypatch.setattr(SqlUserRepository, "lock_administration", lock)
        monkeypatch.setattr(service.selector.claims, "_report", report)
        comparison = asyncio.create_task(
            service.execute(actor, request, preview.comparison_sha256 if export else None)
        )
        deletion = None
        try:
            await asyncio.wait_for(first_checked.wait(), 10)
            deletion = asyncio.create_task(
                delete_report(container, user, first.id), name="comparison-delete"
            )
            await asyncio.wait_for(delete_waiting.wait(), 10)
            await observe_database_lock(container, pids["delete"])
            assert len(set(pids.values())) == 2, "Independent PostgreSQL connections required"
            assert not deletion.done()
            release.set()
            result = await asyncio.wait_for(comparison, 10)
            await asyncio.wait_for(deletion, 10)
            assert result is not None
            assert first.id in checked and second.id in checked
            # Both parent reads succeeded before the mutation could commit.
            assert checked.index(first.id) < checked.index(second.id)
        finally:
            release.set()
            for task in (comparison, deletion):
                if task is not None and not task.done():
                    task.cancel()
            await asyncio.gather(
                *(task for task in (comparison, deletion) if task), return_exceptions=True
            )
    async with container.session_factory() as session:
        reports = container.repositories(session).reports
        assert await reports.get(first.id) is None
        assert await reports.get(second.id) is not None


@pytest.mark.parametrize("export", [False, True], ids=["preview", "export"])
async def test_authorised_deletion_committed_before_final_guard_prevents_delivery(
    client, container, user, export
):
    actor, first, second, request = await two_reports(client, container, user)
    entered, finish = Event(), Event()

    def render(value):
        entered.set()
        assert finish.wait(10)
        return comparison_json(value)

    async with container.session_factory() as session:
        service = container.annotation_comparisons(session)
        preview = await service.execute(actor, request)
        service.renderer = render
        comparison = asyncio.create_task(
            service.execute(actor, request, preview.comparison_sha256 if export else None)
        )
        try:
            assert await asyncio.to_thread(entered.wait, 10)
            await asyncio.wait_for(delete_report(container, user, first.id), 10)
            finish.set()
            with pytest.raises(NotFound):
                await asyncio.wait_for(comparison, 10)
        finally:
            finish.set()
            if not comparison.done():
                comparison.cancel()
            await asyncio.gather(comparison, return_exceptions=True)
    async with container.session_factory() as session:
        assert await container.repositories(session).reports.get(second.id) is not None
