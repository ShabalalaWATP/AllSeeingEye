"""Alert evaluation never waits for report production; admitted work survives restart."""

import asyncio
from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import func, select

from ase.adapters.persistence.report_job_models import ReportJobRow
from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.application.dto import RequestContext
from ase.application.warning.indicators import IndicatorInput
from ase.container.alert_reports import AlertReportAdmission
from assistant_helpers import event
from report_job_api_helpers import job_settings, prepared, stored, submit, work

__all__ = ["job_settings"]


async def rule(container, user, **changes):
    async with container.session_factory() as session:
        return await container.create_indicator(session).execute(
            user,
            IndicatorInput("Report rule", report_template="intsum", **changes),
            RequestContext(),
        )


async def current_alert(container, alert_id):
    async with container.session_factory() as session:
        return await container.repositories(session).alerts.get(alert_id)


async def test_blocked_report_does_not_delay_another_rule_or_the_next_cycle(
    container, user, clock, monkeypatch
):
    for name in ("First", "Second"):
        async with container.session_factory() as session:
            await container.create_indicator(session).execute(
                user,
                IndicatorInput(name, report_template="intsum", cooldown_minutes=1),
                RequestContext(),
            )
    container.store.upsert([event("first-event")])
    entered, release = asyncio.Event(), asyncio.Event()

    async def blocked(*args, **kwargs):
        entered.set()
        await release.wait()
        raise RuntimeError("A report failure must not stop alert evaluation")

    monkeypatch.setattr(
        container, "generate_report", lambda session: SimpleNamespace(execute=blocked)
    )
    evaluator = container.build_evaluator()
    evaluation = asyncio.create_task(evaluator.run_once())
    reporting = asyncio.create_task(entered.wait())
    try:
        async with asyncio.timeout(5):
            done, _ = await asyncio.wait(
                (evaluation, reporting), return_when=asyncio.FIRST_COMPLETED
            )
            assert evaluation in done, "Alert evaluation waited for report production"
            assert len(evaluation.result()) == 2
            assert not entered.is_set()
            clock.advance(timedelta(minutes=2))
            container.store.upsert([replace(event("next-event"), published_at=clock.now())])
            assert len(await evaluator.run_once()) == 2
    finally:
        release.set()
        reporting.cancel()
        evaluation.cancel()
        await asyncio.gather(evaluation, reporting, return_exceptions=True)


async def test_report_intent_survives_admission_restart_and_links_one_completed_job(
    container, user, client
):
    gateway, headers = await prepared(container, client)
    await rule(container, user)
    alert = (await container.build_evaluator().run_once())[0]
    assert (await current_alert(container, alert.id)).report_status == "pending"
    assert gateway.calls == []
    assert await AlertReportAdmission(container).tick() == 1
    queued = await current_alert(container, alert.id)
    assert queued.report_job_id and queued.report_status == "queued" and queued.report_id is None
    assert await AlertReportAdmission(container).tick() == 0
    assert gateway.calls == []
    await work(container)
    completed = await current_alert(container, alert.id)
    assert completed.report_status == "needs_review"
    assert completed.report_job_id == queued.report_job_id and completed.report_id is not None
    calls = len(gateway.calls)
    assert calls > 0
    assert await AlertReportAdmission(container).tick() == 0
    await container.report_job_worker.tick()
    assert len(gateway.calls) == calls
    response = await client.get("/api/warning/alerts", headers=headers)
    assert response.json()["items"][0]["report_status"] == "needs_review"
    assert response.json()["items"][0]["report_job_id"] == str(queued.report_job_id)
    async with container.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(ReportJobRow)) == 1


async def test_model_admission_failure_is_visible_and_does_not_replay(container, user):
    await rule(container, user)
    container.store.upsert([event()])
    alert = (await container.build_evaluator().run_once())[0]
    await AlertReportAdmission(container).tick()  # No model has been configured.
    failed = await current_alert(container, alert.id)
    assert failed.report_status == "failed" and failed.report_error == "admission_failed"
    assert failed.report_job_id is None
    assert await AlertReportAdmission(container).tick() == 0


async def test_expired_report_lease_is_exposed_without_automatic_replay(
    container, user, client, clock
):
    gateway, _ = await prepared(container, client)
    await rule(container, user)
    alert = (await container.build_evaluator().run_once())[0]
    await AlertReportAdmission(container).tick()
    queued = await current_alert(container, alert.id)
    job = await stored(container, queued.report_job_id)
    async with container.session_factory() as session:
        await SqlReportJobRepository(session).claim(
            job.id,
            expected_revision=job.revision,
            lease_token=uuid4(),
            now=clock.now(),
            lease_until=clock.now() + timedelta(seconds=45),
        )
        await session.commit()
    assert (await current_alert(container, alert.id)).report_status == "running"
    clock.advance(timedelta(seconds=46))
    await container.report_job_worker.tick()
    paused = await current_alert(container, alert.id)
    assert paused.report_status == "paused" and paused.report_error == "interrupted_uncertain"
    assert paused.report_job_id == job.id and not gateway.calls
    assert await AlertReportAdmission(container).tick() == 0


async def test_rule_change_before_admission_cancels_the_intent(container, user, clock):
    indicator = await rule(container, user)
    container.store.upsert([event()])
    alert = (await container.build_evaluator().run_once())[0]
    async with container.session_factory() as session:
        await container.repositories(session).indicators.save(
            replace(indicator, enabled=False, updated_at=clock.now() + timedelta(seconds=1))
        )
        await session.commit()
    await AlertReportAdmission(container).tick()
    cancelled = await current_alert(container, alert.id)
    assert cancelled.report_status == "cancelled" and cancelled.report_job_id is None


async def test_full_capacity_defers_admission_without_replaying_paid_work(
    container, user, client, clock
):
    gateway, headers = await prepared(container, client)
    jobs = [(await submit(client, headers)).json()["id"] for _ in range(2)]
    await rule(container, user)
    alert = (await container.build_evaluator().run_once())[0]
    await AlertReportAdmission(container).tick()
    waiting = await current_alert(container, alert.id)
    assert waiting.report_status == "pending" and waiting.report_error == "capacity_wait"
    assert waiting.report_job_id is None and not gateway.calls
    assert await AlertReportAdmission(container).tick() == 0
    assert (
        await client.post(f"/api/report-jobs/{jobs[0]}/pause", headers=headers)
    ).status_code == 200
    clock.advance(timedelta(hours=2))
    assert await AlertReportAdmission(container).tick() == 1
    queued = await current_alert(container, alert.id)
    assert queued.report_status == "queued" and queued.report_job_id is not None
    assert queued.report_error is None and not gateway.calls
    saved = await stored(container, queued.report_job_id)
    assert (
        saved.payload["input"]["period_from"] == (alert.fired_at - timedelta(hours=1)).isoformat()
    )
    assert (
        saved.payload["input"]["period_to"]
        == (alert.fired_at + timedelta(microseconds=1)).isoformat()
    )
    assert await AlertReportAdmission(container).tick() == 0


async def test_expired_admission_is_visible_without_scheduling_stale_reports(
    container, user, client, clock
):
    gateway, _ = await prepared(container, client)
    await rule(container, user)
    alert = (await container.build_evaluator().run_once())[0]
    clock.advance(timedelta(days=1, seconds=1))
    await AlertReportAdmission(container).tick()
    expired = await current_alert(container, alert.id)
    assert expired.report_status == "failed" and expired.report_error == "admission_expired"
    assert expired.report_job_id is None and not gateway.calls
