"""Warm payload caches preserve transaction rollback and current lease checks."""

import asyncio
from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import update

from ase.adapters.persistence.report_job_models import ReportJobRow
from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.adapters.persistence.users import SqlUserRepository
from ase.application.report_jobs.budget import JobInterrupted
from ase.container.report_job_checkpoints import ReportJobCheckpoints
from ase.domain.errors import Forbidden
from report_checkpoint_helpers import CheckpointContainer, current, payload, reservation, usage
from report_job_helpers import NOW, job, saved


@pytest.fixture
def checkpoint_storage(container, user):
    # Uses the ordinary isolated app database, including native PostgreSQL in CI.
    return container, user


async def checkpoint_setup(storage, **changes):
    container, user = storage
    stored = await saved(
        container.session_factory,
        job(
            owner_id=user.id,
            status="running",
            lease_token=uuid4(),
            lease_until=NOW + timedelta(seconds=45),
            payload=payload(**changes),
        ),
    )
    host = CheckpointContainer(container.session_factory)
    return host, stored, ReportJobCheckpoints(host, stored.id, stored.lease_token)


async def test_cancel_after_nested_mutation_preserves_warm_and_fresh_reads(checkpoint_storage):
    host, stored, adapter = await checkpoint_setup(
        checkpoint_storage, nested={"items": [{"value": "retained"}]}, calls=[reservation()]
    )
    before = await adapter._read()
    proposed = asyncio.Event()

    def mutate(data):
        data["nested"]["items"][0]["value"] = "cancelled"
        data["nested"]["items"].append({"value": "uncommitted"})
        data["calls"][0].update(
            status="completed", prompt_tokens=200, completion_tokens=100, latency_ms=250.0
        )

    async def block_proposed(_session, value):
        if value.payload["nested"] != before["nested"]:
            proposed.set()
            await asyncio.Future()

    host.gate_hook = block_proposed
    task = asyncio.create_task(adapter.mutate(mutate))
    try:
        await asyncio.wait_for(proposed.wait(), timeout=5)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    finally:
        if not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        host.gate_hook = None
    assert not host.lock.locked() and not adapter._lock.locked()
    assert await adapter._read() == before
    retained = await current(host, stored.id)
    assert retained.payload == before and retained.revision == stored.revision
    assert await usage(host) == []
    await adapter.mutate(lambda data: data["nested"]["items"].append({"value": "committed"}))
    retained = await current(host, stored.id)
    assert retained.revision == stored.revision + 1
    assert retained.payload["nested"]["items"] == [{"value": "retained"}, {"value": "committed"}]
    assert await usage(host) == []


@pytest.mark.parametrize(
    "change",
    [
        {"status": "paused", "lease_token": None, "lease_until": None},
        {"lease_token": uuid4()},
        {"lease_until": NOW},
    ],
)
async def test_warm_payload_never_reuses_old_lease_state(checkpoint_storage, change):
    host, stored, adapter = await checkpoint_setup(checkpoint_storage, nested={"items": [1]})
    before = await adapter._read()
    async with host.session_factory() as session:
        await session.execute(
            update(ReportJobRow).where(ReportJobRow.id == stored.id).values(**change)
        )
        await session.commit()
    with pytest.raises(JobInterrupted):
        await adapter._read()
    with pytest.raises(JobInterrupted):
        await adapter.mutate(lambda data: data["nested"]["items"].append(2))
    retained = await current(host, stored.id)
    assert retained.payload == before and retained.revision == stored.revision
    assert not host.lock.locked() and not adapter._lock.locked()


async def test_warm_payload_rechecks_revoked_authority(container, user, monkeypatch):
    now = container.clock.now()
    stored = await saved(
        container.session_factory,
        job(
            owner_id=user.id,
            status="running",
            lease_token=uuid4(),
            lease_until=now + timedelta(seconds=45),
        ),
    )

    async def gate(_session, _stored):
        return None

    monkeypatch.setattr(container, "report_job_gate", gate)
    adapter = ReportJobCheckpoints(container, stored.id, stored.lease_token)
    before = await adapter._read()
    async with container.session_factory() as session:
        repository = SqlUserRepository(session)
        await repository.save(replace(user, is_active=False))
        await session.commit()
    with pytest.raises(Forbidden):
        await adapter._read()
    async with container.session_factory() as session:
        retained = await SqlReportJobRepository(session).get(stored.id)
    assert retained.payload == before and retained.revision == stored.revision
