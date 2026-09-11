"""Collection/section durability and live lease/access fences for report workers."""

import asyncio
from datetime import timedelta

import pytest

from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.application.ports.section_checkpoints import SectionCheckpoint
from ase.application.report_jobs.budget import JobInterrupted
from ase.application.reports.production_checkpoint import ProductionSnapshot
from ase.application.reports.production_types import Totals
from ase.application.reports.selection import Selection
from ase.domain.errors import Forbidden
from report_checkpoint_helpers import checkpoint_setup, current
from report_job_helpers import NOW
from report_job_helpers import job_storage as _job_storage  # noqa: F401


async def test_parallel_checkpoints_keep_every_update_and_renew_lease(job_storage):
    host, stored, adapter = await checkpoint_setup(job_storage, counter=0)
    host.now += timedelta(seconds=10)
    await asyncio.gather(
        *[adapter.mutate(lambda data: data.update(counter=data["counter"] + 1)) for _ in range(5)]
    )
    value = await current(host, stored.id)
    assert value.payload["counter"] == 5 and value.revision == 6
    assert value.lease_until == host.now + timedelta(seconds=45)
    assert host.steps == ["access", "gate", "gate"] * 5
    assert value.payload["summary"]["reasoning_effort"] == "max"
    await adapter.check()
    assert host.steps[-2:] == ["access", "gate"]


async def test_expiry_after_awaited_gate_rejects_write(job_storage):
    host, stored, adapter = await checkpoint_setup(job_storage)

    async def expire(_session, _stored):
        host.now = NOW + timedelta(seconds=45)

    host.gate_hook = expire
    with pytest.raises(JobInterrupted):
        await adapter.mutate(lambda data: data.update(counter=1))
    assert (await current(host, stored.id)).revision == 1


async def test_pausing_revokes_old_worker_for_reads_and_writes(job_storage):
    host, stored, adapter = await checkpoint_setup(job_storage)
    async with host.session_factory() as session:
        await SqlReportJobRepository(session).pause(stored.id, expected_revision=1, now=NOW)
        await session.commit()
    with pytest.raises(JobInterrupted):
        await adapter.check()
    with pytest.raises(JobInterrupted):
        await adapter.mutate(lambda data: data.update(counter=1))
    assert host.steps == []


async def test_proposed_new_sources_are_checked_before_checkpoint(job_storage):
    host, stored, adapter = await checkpoint_setup(job_storage)

    async def reject_proposed(_session, value):
        if value.payload.get("new_source"):
            raise Forbidden()

    host.gate_hook = reject_proposed
    with pytest.raises(Forbidden):
        await adapter.mutate(lambda data: data.update(new_source=True))
    assert "new_source" not in (await current(host, stored.id)).payload


async def test_collection_roundtrip_is_immutable_and_survives_adapter_restart(job_storage):
    host, stored, adapter = await checkpoint_setup(job_storage)
    assert await adapter.load_collection() is None
    snapshot = ProductionSnapshot(Selection((), 0, 0), None, None, None, Totals())
    await adapter.save_collection(snapshot)
    restored = type(adapter)(host, stored.id, stored.lease_token)
    assert await restored.load_collection() == snapshot
    await restored.save_collection(snapshot)
    with pytest.raises(JobInterrupted):
        await restored.save_collection(
            ProductionSnapshot(Selection((), 0, 1), None, None, None, Totals())
        )
    assert (await current(host, stored.id)).stage == "drafting"


async def test_sections_are_packet_bound_completed_immutable_and_stage_visible(job_storage):
    host, stored, adapter = await checkpoint_setup(job_storage)
    sections = adapter.section_checkpoints
    first = SectionCheckpoint("completed", {"kind": "topic", "body": {"text": "Saved"}})
    assert await sections.load("a" * 64, "topic") is None
    await sections.save("a" * 64, "topic", first)
    assert await sections.load("a" * 64, "topic") == first
    assert await sections.load("b" * 64, "topic") is None
    await sections.save("a" * 64, "topic", first)
    with pytest.raises(JobInterrupted):
        await sections.save("a" * 64, "topic", SectionCheckpoint("running", {}))
    await sections.save("a" * 64, "synthesis", SectionCheckpoint("running", {"kind": "synthesis"}))
    value = await current(host, stored.id)
    assert value.stage == "summarising"
    assert value.payload["summary"]["completed_sections"] == 1
    assert value.payload["summary"]["total_sections"] == 2


@pytest.mark.parametrize("digest, identity", [("invalid", "a"), ("a" * 64, ""), ("a" * 64, "a\n")])
async def test_section_keys_reject_malformed_identity(job_storage, digest, identity):
    _, _, adapter = await checkpoint_setup(job_storage)
    with pytest.raises(JobInterrupted):
        await adapter.section_checkpoints.load(digest, identity)


async def test_callback_failure_and_cancellation_roll_back(job_storage):
    host, stored, adapter = await checkpoint_setup(job_storage)

    def failed(data):
        data["transient"] = True
        raise RuntimeError("local failure")

    with pytest.raises(RuntimeError):
        await adapter.mutate(failed)
    started = asyncio.Event()

    async def blocked(_session, _stored):
        started.set()
        await asyncio.Future()

    host.gate_hook = blocked
    task = asyncio.create_task(adapter.mutate(lambda data: data.update(transient=True)))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert not host.lock.locked() and (await current(host, stored.id)).revision == 1
