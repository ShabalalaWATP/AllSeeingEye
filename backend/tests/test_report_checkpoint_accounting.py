"""One transaction owns both call settlement and operational usage accounting."""

from copy import deepcopy
from datetime import timedelta

import pytest

from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.application.report_jobs.budget import JobInterrupted
from report_checkpoint_helpers import checkpoint_setup, current, reservation, usage
from report_job_helpers import NOW
from report_job_helpers import job_storage as _job_storage  # noqa: F401


def settle(data, *, status="completed", error=None):
    data["calls"][0].update(
        status=status, prompt_tokens=200, completion_tokens=100, latency_ms=250.0, error=error
    )


async def test_known_usage_is_once_only_and_frozen_with_ledger(job_storage):
    host, stored, adapter = await checkpoint_setup(job_storage, calls=[reservation()])
    await adapter.mutate(settle)
    await adapter.mutate(settle)
    rows = await usage(host)
    assert len(rows) == 1
    assert rows[0].user_id == stored.owner_id and rows[0].purpose == "report-job"
    assert rows[0].prompt_tokens == 200 and rows[0].completion_tokens == 100
    assert rows[0].latency_ms == 250 and rows[0].ok
    assert (await current(host, stored.id)).payload["summary"]["usage"]["output_tokens"] == 100
    with pytest.raises(JobInterrupted):
        await adapter.mutate(lambda data: data["calls"][0].update(completion_tokens=1))
    with pytest.raises(JobInterrupted):
        await adapter.mutate(lambda data: data.update(calls=[]))
    assert len(await usage(host)) == 1


@pytest.mark.parametrize(
    "status, error, count",
    [("failed", "token_budget_exhausted", 1), ("uncertain", "interrupted", 0)],
)
async def test_failure_and_uncertainty_have_honest_reservations(job_storage, status, error, count):
    host, stored, adapter = await checkpoint_setup(job_storage, calls=[reservation()])
    await adapter.mutate(lambda data: settle(data, status=status, error=error))
    rows = await usage(host)
    assert len(rows) == count
    expected = 100 if status == "failed" else 32000
    assert (await current(host, stored.id)).payload["summary"]["usage"]["output_tokens"] == expected
    if rows:
        assert rows[0].error == error and not rows[0].ok


async def test_lost_cas_rolls_usage_back_with_checkpoint(job_storage, monkeypatch):
    host, stored, adapter = await checkpoint_setup(job_storage, calls=[reservation()])

    async def lost(_self, *_args, **_kwargs):
        return None

    monkeypatch.setattr(SqlReportJobRepository, "checkpoint", lost)
    with pytest.raises(JobInterrupted):
        await adapter.mutate(settle)
    assert await usage(host) == []
    assert (await current(host, stored.id)).payload["calls"][0]["status"] == "in_flight"


async def test_expiry_during_accounting_rolls_back_before_checkpoint(job_storage, monkeypatch):
    host, stored, adapter = await checkpoint_setup(job_storage, calls=[reservation()])
    original = adapter._account

    async def delayed(session, job, data):
        await original(session, job, data)
        host.now = NOW + timedelta(seconds=46)

    monkeypatch.setattr(adapter, "_account", delayed)
    with pytest.raises(JobInterrupted):
        await adapter.mutate(settle)
    assert await usage(host) == [] and (await current(host, stored.id)).revision == 1


@pytest.mark.parametrize("needs_review", [False, True])
async def test_finish_never_commits_and_usage_rolls_back_with_final_state(
    job_storage, needs_review
):
    host, stored, adapter = await checkpoint_setup(job_storage, calls=[reservation()])
    data = deepcopy(stored.payload)
    settle(data)
    async with host.guard(), host.session_factory() as session:
        final = await adapter.finish(session, data, needs_review)
        assert final.status == ("needs_review" if needs_review else "completed")
        await session.rollback()
    assert await usage(host) == [] and (await current(host, stored.id)).status == "running"
    async with host.guard(), host.session_factory() as session:
        await adapter.finish(session, data, needs_review)
        await session.commit()
    assert len(await usage(host)) == 1
    async with host.guard(), host.session_factory() as session:
        with pytest.raises(JobInterrupted):
            await adapter.finish(session, data, needs_review)


async def test_lost_final_cas_leaves_callers_transaction_uncommitted(job_storage, monkeypatch):
    host, stored, adapter = await checkpoint_setup(job_storage, calls=[reservation()])
    data = deepcopy(stored.payload)
    settle(data)

    async def lost(_self, *_args, **_kwargs):
        return None

    monkeypatch.setattr(SqlReportJobRepository, "complete", lost)
    async with host.guard(), host.session_factory() as session:
        with pytest.raises(JobInterrupted):
            await adapter.finish(session, data)
        await session.rollback()
    assert await usage(host) == [] and (await current(host, stored.id)).status == "running"
