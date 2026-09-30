"""Cached parsing is never cached authority or a substitute for byte integrity."""

import hashlib
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import event, update

from ase.adapters.persistence import report_job_codec
from ase.adapters.persistence.report_job_codec import PayloadCache
from ase.adapters.persistence.report_job_models import ReportJobRow
from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.adapters.store.memory import InMemoryEventStore
from ase.application.report_jobs.budget import JobInterrupted
from ase.application.report_jobs.snapshots import freeze_job
from ase.container import report_job_cache
from ase.container.report_job_checkpoints import ReportJobCheckpoints
from ase.domain.errors import Conflict
from helpers import FakeClock
from report_job_helpers import NOW, job, saved
from report_job_helpers import job_storage as _job_storage  # noqa: F401
from report_job_snapshot_helpers import fixture_job, fixture_routing


@pytest.mark.parametrize("invalid_version", [99, True, 1.0])
def test_admission_restores_once_and_refreshes_actor_without_mutable_aliases(
    monkeypatch, invalid_version
):
    value = fixture_job()
    frozen = freeze_job(value, fixture_routing(value), {}, InMemoryEventStore)
    restore = report_job_cache.restore_job
    counts = []

    def counted(*args):
        counts.append(1)
        return restore(*args)

    monkeypatch.setattr(report_job_cache, "restore_job", counted)
    cache = report_job_cache.AttemptCache()
    first = cache.restore(frozen, value.actor, value.profile)
    first.scope["changed"] = True
    actor = replace(value.actor, display_name="Current actor")
    second = cache.restore(deepcopy(frozen), actor, value.profile)
    assert len(counts) == 1 and "changed" not in second.scope
    assert second.actor is actor
    changed = deepcopy(frozen)
    changed["schema_version"] = invalid_version
    with pytest.raises(ValueError):
        cache.restore(changed, actor, value.profile)
    assert len(counts) == 2


def test_cached_input_does_not_alias_tuple_to_validated_json_array():
    value = fixture_job()
    frozen = freeze_job(value, fixture_routing(value), {}, InMemoryEventStore)
    cache = report_job_cache.AttemptCache()
    cache.restore(frozen, value.actor, value.profile)
    changed = deepcopy(frozen)
    changed["evidence"] = tuple(changed["evidence"])
    with pytest.raises(ValueError, match="JSON arrays"):
        cache.restore(changed, value.actor, value.profile)


async def test_cached_bytes_are_validated_once_and_never_share_payload_aliases(
    job_storage, monkeypatch
):
    _, factory = job_storage
    stored = await saved(factory, job())
    cache = PayloadCache()
    original = report_job_codec.canonical_job_payload
    validations = []

    def count(payload):
        validations.append(1)
        return original(payload)

    monkeypatch.setattr(report_job_codec, "canonical_job_payload", count)
    async with factory() as session:
        repository = SqlReportJobRepository(session, cache)
        first = await repository.get(stored.id)
        first.payload["summary"]["completed_sections"] = 999
        second = await repository.get(stored.id)
        assert second.payload == stored.payload and len(validations) == 1


@pytest.mark.parametrize(
    "raw,refresh_hash",
    [
        ('{"schema_version":1,"summary":{"completed_sections":99}}', False),
        ('{ "schema_version": 1 }', True),
        ('{"schema_version":2}', True),
    ],
)
async def test_cached_checkpoint_still_rejects_tampered_actual_bytes(
    job_storage, raw, refresh_hash
):
    _, factory = job_storage
    stored = await saved(factory, job())
    async with factory() as session:
        repository = SqlReportJobRepository(session, PayloadCache())
        assert await repository.get(stored.id)
        values = {"payload": raw, "payload_bytes": len(raw.encode())}
        if refresh_hash:
            values["payload_sha256"] = hashlib.sha256(raw.encode()).hexdigest()
        await session.execute(
            update(ReportJobRow).where(ReportJobRow.id == stored.id).values(**values)
        )
        await session.commit()
        with pytest.raises(Conflict):
            await repository.get(stored.id)


async def test_heartbeat_only_updates_lease_and_checks_authority_each_time(job_storage):
    engine, factory = job_storage
    token = uuid4()
    stored = await saved(
        factory,
        job(
            status="running",
            lease_token=token,
            lease_until=NOW + timedelta(seconds=20),
        ),
    )

    class Guard:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

    access = SimpleNamespace(background=AsyncMock())
    container = SimpleNamespace(
        clock=FakeClock(NOW),
        session_factory=factory,
        source_admission=SimpleNamespace(guard=Guard),
        access_policy=lambda session: access,
        report_job_gate=AsyncMock(),
    )
    checkpoints = ReportJobCheckpoints(container, stored.id, token)
    statements = []

    def capture(_c, _cu, sql, _p, _cx, _m):
        statements.append(sql)

    event.listen(engine.sync_engine, "before_cursor_execute", capture)
    try:
        await checkpoints.renew_lease()
        await checkpoints.renew_lease()
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", capture)
    writes = [sql for sql in statements if sql.startswith("UPDATE")]
    assert len(writes) == 2 and all(
        "SET lease_until=" in sql and "payload" not in sql for sql in writes
    )
    assert access.background.await_count == container.report_job_gate.await_count == 2
    async with factory() as session:
        restored = await SqlReportJobRepository(session).get(stored.id)
    assert restored.revision == stored.revision and restored.payload == stored.payload
    assert restored.lease_until == NOW + timedelta(seconds=45)


@pytest.mark.parametrize(
    "change",
    [
        {"revision": 2},
        {"status": "paused", "lease_token": None, "lease_until": None},
        {"lease_token": uuid4()},
        {"lease_until": NOW},
    ],
)
async def test_lease_only_renewal_cannot_extend_a_changed_attempt(job_storage, change):
    _, factory = job_storage
    token = uuid4()
    stored = await saved(
        factory,
        job(
            status="running",
            lease_token=token,
            lease_until=NOW + timedelta(seconds=20),
        ),
    )

    class Guard:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

    async def changed_after_read(session, current):
        await session.execute(
            update(ReportJobRow).where(ReportJobRow.id == stored.id).values(**change)
        )

    container = SimpleNamespace(
        clock=FakeClock(NOW),
        session_factory=factory,
        source_admission=SimpleNamespace(guard=Guard),
        access_policy=lambda session: SimpleNamespace(background=AsyncMock()),
        report_job_gate=changed_after_read,
    )
    with pytest.raises(JobInterrupted):
        await ReportJobCheckpoints(container, stored.id, token).renew_lease()
    async with factory() as session:
        retained = await SqlReportJobRepository(session).get(stored.id)
        assert retained == stored
