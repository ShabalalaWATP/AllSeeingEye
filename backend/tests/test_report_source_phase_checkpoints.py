"""Lease-fenced source operations commit on either side of outbound work."""

from datetime import timedelta

import pytest

from ase.application.report_jobs.budget import JobInterrupted
from ase.application.research.phase_ledger import (
    LEDGER_KEY,
    PhaseLedgerError,
    new_phase_ledger,
)
from ase.domain.research import ResearchMode
from report_checkpoint_helpers import checkpoint_setup, current
from report_job_helpers import NOW
from report_job_helpers import job_storage as _job_storage  # noqa: F401


async def test_existing_job_without_ledger_is_left_unchanged(job_storage):
    host, stored, checkpoints = await checkpoint_setup(job_storage)
    original = await current(host, stored.id)
    with pytest.raises(PhaseLedgerError, match="absent"):
        await checkpoints.reserve_source_operation(
            mode=ResearchMode.DETAILED, phase="initial", request_key="source:1"
        )
    assert (await current(host, stored.id)).revision == original.revision
    assert LEDGER_KEY not in (await current(host, stored.id)).payload


async def test_reserve_commits_before_network_and_settle_survives_restart(job_storage):
    mode = ResearchMode.DETAILED
    host, stored, checkpoints = await checkpoint_setup(
        job_storage, source_phase_ledger=new_phase_ledger(mode)
    )
    decision = await checkpoints.reserve_source_operation(
        mode=mode, phase="initial", request_key="source:1"
    )
    assert decision.dispatch and decision.allowance_ms == 20_000
    assert not host.lock.locked()
    persisted = await current(host, stored.id)
    assert persisted.revision == 2
    open_request = persisted.payload[LEDGER_KEY]["phases"]["initial"]["operations"]["source:1"]
    assert open_request["status"] == "open" and open_request["charged_ms"] == 20_000

    restarted = type(checkpoints)(host, stored.id, stored.lease_token)
    replay = await restarted.reserve_source_operation(
        mode=mode, phase="initial", request_key="source:1"
    )
    assert replay.status == "open" and not replay.dispatch
    settled = await restarted.settle_source_operation(
        mode=mode,
        phase="initial",
        request_key="source:1",
        elapsed_ms=1_200,
        retained_item_keys=("evidence:1", "evidence:1", "evidence:2"),
    )
    assert settled.charged_ms == 1_200
    assert settled.retained_keys == ("evidence:1", "evidence:2")
    assert not host.lock.locked()
    after = await current(host, stored.id)
    operation = after.payload[LEDGER_KEY]["phases"]["initial"]["operations"]["source:1"]
    assert operation["status"] == "settled" and operation["charged_ms"] == 1_200
    assert (
        await restarted.settle_source_operation(
            mode=mode,
            phase="initial",
            request_key="source:1",
            elapsed_ms=1_200,
            retained_item_keys=("evidence:1", "evidence:2"),
        )
        == settled
    )
    assert not (
        await restarted.reserve_source_operation(mode=mode, phase="initial", request_key="source:1")
    ).dispatch


async def test_open_phase_is_serial_and_recovery_keeps_unknown_charge(job_storage):
    mode = ResearchMode.QUICK
    host, stored, checkpoints = await checkpoint_setup(
        job_storage, source_phase_ledger=new_phase_ledger(mode)
    )
    await checkpoints.reserve_source_operation(mode=mode, phase="initial", request_key="lost")
    blocked = await checkpoints.reserve_source_operation(
        mode=mode, phase="initial", request_key="other"
    )
    assert blocked.reason == "operation_open" and not blocked.dispatch
    restarted = type(checkpoints)(host, stored.id, stored.lease_token)
    unknown = await restarted.abandon_source_operation(
        mode=mode, phase="initial", request_key="lost"
    )
    assert unknown.status == "unknown" and not unknown.dispatch
    with pytest.raises(PhaseLedgerError, match="abandoned"):
        await restarted.settle_source_operation(
            mode=mode,
            phase="initial",
            request_key="lost",
            elapsed_ms=0,
            retained_item_keys=(),
        )
    next_decision = await restarted.reserve_source_operation(
        mode=mode, phase="initial", request_key="other"
    )
    assert next_decision.dispatch
    operations = (await current(host, stored.id)).payload[LEDGER_KEY]["phases"]["initial"][
        "operations"
    ]
    assert operations["lost"]["charged_ms"] == 12_000
    assert operations["other"]["charged_ms"] == 12_000


async def test_lease_expiry_rejects_reservation_without_persisting(job_storage):
    mode = ResearchMode.ADVANCED
    host, stored, checkpoints = await checkpoint_setup(
        job_storage, source_phase_ledger=new_phase_ledger(mode)
    )
    host.now = NOW + timedelta(seconds=45)
    with pytest.raises(JobInterrupted):
        await checkpoints.reserve_source_operation(
            mode=mode, phase="initial", request_key="too-late"
        )
    after = await current(host, stored.id)
    assert after.revision == 1
    assert after.payload[LEDGER_KEY]["phases"]["initial"]["operations"] == {}


async def test_expired_worker_cannot_settle_an_open_request(job_storage):
    mode = ResearchMode.DETAILED
    host, stored, checkpoints = await checkpoint_setup(
        job_storage, source_phase_ledger=new_phase_ledger(mode)
    )
    await checkpoints.reserve_source_operation(mode=mode, phase="initial", request_key="in-flight")
    host.now = NOW + timedelta(seconds=45)
    with pytest.raises(JobInterrupted):
        await checkpoints.settle_source_operation(
            mode=mode,
            phase="initial",
            request_key="in-flight",
            elapsed_ms=1_000,
            retained_item_keys=("uncommitted",),
        )
    operation = (await current(host, stored.id)).payload[LEDGER_KEY]["phases"]["initial"][
        "operations"
    ]["in-flight"]
    assert operation["status"] == "open"
    assert operation["charged_ms"] == 20_000
    assert operation["retained_keys"] == []


async def test_failed_gate_rolls_back_reserved_allowance(job_storage):
    mode = ResearchMode.DETAILED
    host, stored, checkpoints = await checkpoint_setup(
        job_storage, source_phase_ledger=new_phase_ledger(mode)
    )

    async def revoke(_session, proposed):
        if proposed.payload[LEDGER_KEY]["phases"]["initial"]["operations"]:
            raise JobInterrupted()

    host.gate_hook = revoke
    with pytest.raises(JobInterrupted):
        await checkpoints.reserve_source_operation(
            mode=mode, phase="initial", request_key="rejected"
        )
    after = await current(host, stored.id)
    assert after.revision == 1
    assert after.payload[LEDGER_KEY]["phases"]["initial"]["operations"] == {}
