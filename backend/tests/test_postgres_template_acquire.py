"""Acquisition rechecks awaited initialisation without recompiling a warm guard twice."""

import asyncio
from types import SimpleNamespace

import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table, event

import postgres_template_guard as guard
import postgres_template_store as store


@pytest.fixture
def acquisition(monkeypatch):
    metadata = MetaData()
    table = Table(
        "example", metadata, Column("id", Integer, primary_key=True), Column("name", String(20))
    )
    monkeypatch.setattr(guard, "Base", SimpleNamespace(metadata=metadata))
    monkeypatch.setattr(guard, "_METADATA", metadata)
    worker = store.TemplateWorker(
        "postgresql+asyncpg://localhost/ase_test_" + "a" * 32 + "_master",
        guard.schema_fingerprint(),
    )
    phases, fingerprints = [], []
    state = SimpleNamespace(block=None, entered=asyncio.Event(), resume=asyncio.Event())

    async def phase(name):
        phases.append(name)
        if state.block == name:
            state.entered.set()
            await state.resume.wait()

    async def dispose():
        await phase("dispose")

    async def create_schema(_engine, *, fresh):
        assert fresh
        await phase("schema")

    async def command(name, *, clone=False, drop=False, seal=False):
        worker._validate(name)
        if drop:
            worker._created.remove(name)
            worker._leases.pop(name, None)
            await phase("drop")
        elif seal:
            assert name in worker._created
            await phase("seal")
        else:
            if clone:
                assert worker.template in worker._created
            worker._created.add(name)
            await phase("clone" if clone else "create")

    def fingerprint():
        result = guard.schema_fingerprint()
        fingerprints.append(result)
        return result

    monkeypatch.setattr(store, "schema_fingerprint", fingerprint)
    monkeypatch.setattr(store, "instrumented", lambda _engine: False)
    monkeypatch.setattr(store, "create_engine", lambda _url: SimpleNamespace(dispose=dispose))
    monkeypatch.setattr(store, "create_schema", create_schema)
    monkeypatch.setattr(worker, "_command", command)
    return SimpleNamespace(
        worker=worker,
        metadata=metadata,
        column=table.c.name,
        phases=phases,
        fingerprints=fingerprints,
        state=state,
    )


async def test_first_and_warm_acquisitions_keep_owned_independent_leases(acquisition):
    probe = acquisition
    first = await probe.worker.acquire()
    assert first is not None
    assert probe.phases == ["create", "schema", "dispose", "seal", "clone"]
    assert probe.fingerprints == [probe.worker.fingerprint] * 2
    second = await probe.worker.acquire()
    assert second is not None and second.name != first.name
    assert probe.fingerprints == [probe.worker.fingerprint] * 3
    assert probe.phases == ["create", "schema", "dispose", "seal", "clone", "clone"]
    assert probe.worker._leases == {first.name: first, second.name: second}
    assert probe.worker._created == {probe.worker.template, first.name, second.name}
    await probe.worker.release(first)
    assert probe.worker._leases == {second.name: second}
    await probe.worker.close()
    assert not probe.worker._created and not probe.worker._leases


def observe(*_args, **_kwargs):
    pytest.fail("Acquisition must not invoke a DDL observer")


@pytest.mark.parametrize("mutation", ["column", "observer"])
async def test_warm_metadata_rejection_precedes_allocation_and_database_commands(
    acquisition, mutation
):
    probe = acquisition
    first = await probe.worker.acquire()
    assert first is not None
    await probe.worker.release(first)
    allocated, phases = set(probe.worker._allocated), list(probe.phases)
    if mutation == "column":
        probe.column.type.length = 80
    else:
        event.listen(probe.metadata, "before_create", observe)
    try:
        assert await probe.worker.acquire() is None
        assert probe.worker._allocated == allocated and probe.phases == phases
        assert probe.worker._created == {probe.worker.template}
        assert not probe.worker._leases
    finally:
        if mutation == "observer":
            event.remove(probe.metadata, "before_create", observe)
        await probe.worker.close()


@pytest.mark.parametrize("phase", ["create", "schema", "dispose", "seal"])
@pytest.mark.parametrize("mutation", ["column", "observer"])
async def test_change_during_awaited_initialisation_rejects_clone_but_retains_cleanup(
    acquisition, phase, mutation
):
    probe = acquisition
    probe.state.block = phase
    pending = asyncio.create_task(probe.worker.acquire())
    try:
        async with asyncio.timeout(2):
            await probe.state.entered.wait()
            assert not pending.done()
            if mutation == "column":
                probe.column.nullable = not probe.column.nullable
            else:
                event.listen(probe.metadata, "after_create", observe)
            probe.state.resume.set()
            assert await pending is None
        assert probe.phases == ["create", "schema", "dispose", "seal"]
        assert probe.worker.template in probe.worker._created
        assert len(probe.worker._allocated) == 1 and not probe.worker._leases
        assert probe.fingerprints[0] == probe.worker.fingerprint
        assert probe.fingerprints[1] != probe.worker.fingerprint
    finally:
        probe.state.resume.set()
        await asyncio.gather(pending, return_exceptions=True)
        if event.contains(probe.metadata, "after_create", observe):
            event.remove(probe.metadata, "after_create", observe)
        await probe.worker.close()
    assert not probe.worker._created


async def test_missing_initial_fingerprint_performs_no_schema_or_database_work(acquisition):
    probe = acquisition
    probe.worker.fingerprint = None
    assert await probe.worker.acquire() is None
    assert not probe.phases and not probe.fingerprints and not probe.worker._allocated
