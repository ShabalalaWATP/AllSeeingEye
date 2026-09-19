"""Real worker restart and final transaction boundaries with synthetic provider calls."""

import asyncio
from datetime import timedelta
from uuid import UUID, uuid4

import pytest

from ase.adapters.persistence.audit import SqlAlchemyUnitOfWork
from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.container.report_job_checkpoints import ReportJobCheckpoints
from ase.container.report_job_worker import ReportJobWorker
from report_job_api_helpers import job_settings, prepared, stored, submit, work

__all__ = ["job_settings"]


def hold_next_call(gateway, monkeypatch):
    entered, release = asyncio.Event(), asyncio.Event()
    original = gateway.complete

    async def blocked(*args):
        entered.set()
        await release.wait()
        return await original(*args)

    monkeypatch.setattr(gateway, "complete", blocked)
    return entered, release


async def test_shutdown_retains_uncertain_paid_reservation_and_requires_explicit_resume(
    client, user, container, monkeypatch
):
    gateway, headers = await prepared(container, client)
    job_id = (await submit(client, headers)).json()["id"]
    entered, _ = hold_next_call(gateway, monkeypatch)
    worker = container.report_job_worker
    await worker.tick()
    await asyncio.wait_for(entered.wait(), 15)
    assert (await stored(container, job_id)).payload["calls"][0]["status"] == "in_flight"
    await asyncio.wait_for(worker.stop(), 15)
    paused = await stored(container, job_id)
    assert paused.status == "paused" and paused.error == "interrupted"
    assert paused.payload["calls"][0]["status"] == "uncertain"
    assert paused.payload["calls"][0]["reserved_output"] == 32000
    restart = ReportJobWorker(container)
    await restart.tick()
    assert not restart._running
    assert (await stored(container, job_id)).payload["calls"] == paused.payload["calls"]
    assert not gateway.calls


async def test_expired_lease_recovery_never_replays_provider_call_automatically(
    client, user, container
):
    gateway, headers = await prepared(container, client)
    job_id = (await submit(client, headers)).json()["id"]
    queued = await stored(container, job_id)
    async with container.session_factory() as session:
        claimed = await SqlReportJobRepository(session).claim(
            queued.id,
            expected_revision=queued.revision,
            lease_token=uuid4(),
            now=container.clock.now(),
            lease_until=container.clock.now() + timedelta(seconds=45),
        )
        await session.commit()
    assert claimed is not None
    container.clock.advance(timedelta(seconds=46))
    restarted = ReportJobWorker(container)
    await restarted.tick()
    paused = await stored(container, job_id)
    assert paused.status == "paused" and paused.error == "interrupted_uncertain"
    assert paused.lease_token is None and not restarted._running and not gateway.calls
    await restarted.tick()
    assert (await stored(container, job_id)).revision == paused.revision


async def test_old_lease_cancel_cannot_interrupt_replacement_worker(
    client, user, container, monkeypatch
):
    gateway, headers = await prepared(container, client)
    job_id = (await submit(client, headers)).json()["id"]
    entered, release = hold_next_call(gateway, monkeypatch)
    worker = container.report_job_worker
    await worker.tick()
    await asyncio.wait_for(entered.wait(), 15)
    old_token, old_task = worker._running[UUID(job_id)]
    await worker.stop()
    assert old_task.done()
    response = await client.post(f"/api/report-jobs/{job_id}/resume", headers=headers)
    assert response.status_code == 202, response.text
    entered.clear()
    await worker.tick()
    await asyncio.wait_for(entered.wait(), 15)
    new_token, new_task = worker._running[UUID(job_id)]
    assert new_token != old_token
    worker.cancel(UUID(job_id), old_token)
    await asyncio.sleep(0)
    assert not new_task.done() and not new_task.cancelling()
    release.set()
    await asyncio.wait_for(new_task, 20)
    final = await stored(container, job_id)
    # The synthetic draft lacks enough original source context for automatic release.
    # Lease replacement still finishes the same job without replaying the uncertain call.
    assert final.status == "needs_review", final.error
    assert len(final.payload["calls"]) == 11 and len(gateway.calls) == 10
    assert final.payload["calls"][0]["status"] == "uncertain"


@pytest.mark.parametrize("acknowledgement_lost", [False, True])
async def test_final_commit_failure_is_atomic_and_next_tick_does_not_duplicate_report(
    client, user, container, monkeypatch, acknowledgement_lost
):
    gateway, headers = await prepared(container, client)
    job_id = (await submit(client, headers)).json()["id"]
    original_finish = ReportJobCheckpoints.finish
    original_commit = SqlAlchemyUnitOfWork.commit

    async def finish(self, session, *args, **kwargs):
        result = await original_finish(self, session, *args, **kwargs)
        session.info["test_final_report_commit"] = True
        return result

    async def commit(self):
        if self._session.info.pop("test_final_report_commit", False):
            if acknowledgement_lost:
                await original_commit(self)
            raise RuntimeError("Synthetic final transaction interruption")
        await original_commit(self)

    monkeypatch.setattr(ReportJobCheckpoints, "finish", finish)
    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", commit)
    await work(container)
    final = await stored(container, job_id)
    assert final.status == ("needs_review" if acknowledgement_lost else "paused")
    async with container.session_factory() as session:
        repo = container.repositories(session).reports
        reports = await repo.list_recent(10)
        version = await repo.get_version(final.report_id, 1)
    assert len(reports) == int(acknowledgement_lost)
    assert (version is not None) == acknowledgement_lost
    await container.report_job_worker.tick()
    # Seven drafting calls, analysis, entailment and claim extraction; the retry
    # replays none of them.
    assert len(gateway.calls) == 10 and not container.report_job_worker._running
    assert (await stored(container, job_id)).revision == final.revision
