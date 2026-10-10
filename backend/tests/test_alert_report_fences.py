"""An alert's origin and durable admission must remain authoritative across awaits."""

import asyncio
from dataclasses import replace
from datetime import timedelta

from sqlalchemy import func, select

from ase.adapters.persistence.audit import SqlAlchemyUnitOfWork
from ase.adapters.persistence.report_job_models import ReportJobRow
from ase.application.dto import RequestContext
from ase.application.report_jobs.service import ReportJobService
from ase.container.alert_reports import AlertReportAdmission
from assistant_helpers import event
from report_job_api_helpers import job_settings, prepared, work
from team_helpers import CONTEXT, team_service
from test_alert_report_queue import current_alert, rule
from test_report_job_worker_integration import hold_next_call
from warning_scope_helpers import warning_actors

__all__ = ["job_settings", "warning_actors"]


async def test_cancelled_preparation_keeps_a_recoverable_intent(
    container, client, user, monkeypatch
):
    gateway, _ = await prepared(container, client)
    await rule(container, user)
    alert = (await container.build_evaluator().run_once())[0]
    entered, release = asyncio.Event(), asyncio.Event()
    original = ReportJobService.prepare_candidate

    async def blocked(self, *args, **kwargs):
        entered.set()
        await release.wait()
        return await original(self, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(ReportJobService, "prepare_candidate", blocked)
        task = asyncio.create_task(AlertReportAdmission(container).tick())
        try:
            await asyncio.wait_for(entered.wait(), 5)
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
    assert (await current_alert(container, alert.id)).report_status == "pending"
    assert not gateway.calls
    await AlertReportAdmission(container).tick()
    assert (await current_alert(container, alert.id)).report_status == "queued"
    assert not gateway.calls


async def test_duplicate_admission_preparation_commits_only_one_job(
    container, client, user, monkeypatch
):
    gateway, _ = await prepared(container, client)
    await rule(container, user)
    alert = (await container.build_evaluator().run_once())[0]
    prepared_both, release = asyncio.Event(), asyncio.Event()
    original = ReportJobService.prepare_candidate
    count = 0

    async def barrier(self, *args, **kwargs):
        nonlocal count
        candidate = await original(self, *args, **kwargs)
        count += 1
        if count == 2:
            prepared_both.set()
        await release.wait()
        return candidate

    monkeypatch.setattr(ReportJobService, "prepare_candidate", barrier)
    tasks = [asyncio.create_task(AlertReportAdmission(container).tick()) for _ in range(2)]
    try:
        await asyncio.wait_for(prepared_both.wait(), 10)
        release.set()
        await asyncio.wait_for(asyncio.gather(*tasks), 10)
    finally:
        release.set()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    current = await current_alert(container, alert.id)
    assert current.report_status == "queued" and current.report_job_id is not None
    async with container.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(ReportJobRow)) == 1
    assert not gateway.calls


async def test_lost_admission_commit_acknowledgement_preserves_one_link(
    container, client, user, monkeypatch
):
    gateway, _ = await prepared(container, client)
    await rule(container, user)
    alert = (await container.build_evaluator().run_once())[0]
    original = SqlAlchemyUnitOfWork.commit
    interrupted = False

    async def commit_then_lose_acknowledgement(self):
        nonlocal interrupted
        await original(self)
        if not interrupted:
            interrupted = True
            raise OSError("Synthetic lost commit acknowledgement")

    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", commit_then_lose_acknowledgement)
    await AlertReportAdmission(container).tick()
    current = await current_alert(container, alert.id)
    assert interrupted and current.report_status == "queued" and current.report_job_id is not None
    assert await AlertReportAdmission(container).tick() == 0
    async with container.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(ReportJobRow)) == 1
    assert not gateway.calls


async def test_paused_rule_fences_queued_execution_before_paid_work(container, client, user, clock):
    gateway, _ = await prepared(container, client)
    indicator = await rule(container, user)
    alert = (await container.build_evaluator().run_once())[0]
    await AlertReportAdmission(container).tick()
    async with container.session_factory() as session:
        await container.repositories(session).indicators.save(
            replace(indicator, enabled=False, updated_at=clock.now() + timedelta(seconds=1))
        )
        await session.commit()
    await work(container)
    current = await current_alert(container, alert.id)
    assert current.report_status == "paused" and current.report_error == "access_changed"
    assert current.report_id is None and not gateway.calls


async def test_revoked_owner_stops_publication_and_preserves_progress(
    container, client, user, admin, monkeypatch
):
    gateway, _ = await prepared(container, client)
    await rule(container, user)
    alert = (await container.build_evaluator().run_once())[0]
    await AlertReportAdmission(container).tick()
    entered, release = hold_next_call(gateway, monkeypatch)
    worker = container.report_job_worker
    await worker.tick()
    try:
        await asyncio.wait_for(entered.wait(), 15)
        async with container.session_factory() as session:
            await container.update_user(session).execute(
                admin, user.id, None, False, RequestContext()
            )
        release.set()
        await asyncio.wait_for(asyncio.gather(*(task for _, task in worker._running.values())), 15)
    finally:
        release.set()
        await worker.stop()
    current = await current_alert(container, alert.id)
    assert current.report_status == "paused" and current.report_id is None
    assert current.report_job_id is not None


async def test_team_membership_removal_fences_queued_report(
    container, client, admin, warning_actors
):
    gateway, _ = await prepared(container, client)
    actors = warning_actors
    await rule(container, actors.owner, team_id=actors.team.id)
    alert = (await container.build_evaluator().run_once())[0]
    await AlertReportAdmission(container).tick()
    assert (await current_alert(container, alert.id)).report_status == "queued"
    async with team_service(container) as service:
        await service.remove_member(admin, actors.team.id, actors.owner.id, CONTEXT)
    await work(container)
    current = await current_alert(container, alert.id)
    assert current.report_status == "paused" and current.report_id is None
    assert not gateway.calls


async def test_blocked_failing_worker_does_not_delay_later_rules_or_cycles(
    container, client, user, clock, monkeypatch
):
    gateway, _ = await prepared(container, client)
    await rule(container, user, cooldown_minutes=1)
    evaluator = container.build_evaluator()
    alert = (await evaluator.run_once())[0]
    await AlertReportAdmission(container).tick()
    entered, release = asyncio.Event(), asyncio.Event()

    async def blocked_failure(*args):
        entered.set()
        await release.wait()
        raise RuntimeError("Synthetic provider failure")

    monkeypatch.setattr(gateway, "complete", blocked_failure)
    worker = container.report_job_worker
    await worker.tick()
    try:
        await asyncio.wait_for(entered.wait(), 15)
        await rule(container, user, cooldown_minutes=1)
        for index in range(2):
            clock.advance(timedelta(minutes=2))
            container.store.upsert(
                [replace(event(f"later-event-{index}"), published_at=clock.now())]
            )
            assert len(await asyncio.wait_for(evaluator.run_once(), 5)) == 2
        assert (await current_alert(container, alert.id)).report_status == "running"
        release.set()
        await asyncio.wait_for(asyncio.gather(*(task for _, task in worker._running.values())), 15)
    finally:
        release.set()
        await worker.stop()
    current = await current_alert(container, alert.id)
    assert current.report_status == "paused" and current.report_error is not None
    assert current.report_id is None and current.report_job_id is not None
