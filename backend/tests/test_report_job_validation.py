"""Checkpoint codec and state-boundary validation, including malformed retained data."""

import hashlib
from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from ase.adapters.persistence.report_job_models import ReportJobRow
from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.domain.errors import Conflict
from ase.domain.report_jobs import canonical_job_payload, job_lease
from report_job_helpers import NOW, job, saved
from report_job_helpers import job_storage as _job_storage  # noqa: F401


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"schema_version": True},
        {"schema_version": 2},
        {"schema_version": 1, "nested": {"api_key_encrypted": "fixture"}},
        {"schema_version": 1, "nested": {4: "not a string key"}},
        {"schema_version": 1, "x" * 201: None},
        {"schema_version": 1, "value": float("nan")},
        {"schema_version": 1, "value": object()},
        {"schema_version": 1, "value": "x" * (2 * 1024 * 1024 + 1)},
        {"schema_version": 1, "value": "世" * (1024 * 1024)},
        {"schema_version": 1, "value": [None] * 200_001},
        {"schema_version": 1, "summary": ["wrong shape"]},
        {"schema_version": 1, "summary": {"text": "x" * 8192}},
        {"schema_version": 1, "value": "\ud800"},
    ],
    ids=[
        "missing-version",
        "boolean-version",
        "future-version",
        "credential-field",
        "key-type",
        "key-size",
        "nonfinite",
        "object",
        "oversized",
        "utf8-size",
        "node-budget",
        "summary-shape",
        "summary-budget",
        "invalid-unicode",
    ],
)
def test_checkpoint_rejects_unsupported_or_unbounded_payload(payload):
    with pytest.raises(ValueError):
        canonical_job_payload(payload)


def test_cycle_and_extreme_nesting_are_rejected_before_json_encoding():
    payload = {"schema_version": 1}
    payload["cycle"] = payload
    with pytest.raises(ValueError, match="too complex"):
        canonical_job_payload(payload)


def test_canonical_json_roundtrip_preserves_types_and_ignores_dictionary_order():
    one = {"schema_version": 1, "data": (True, False, None, 1.5, {"label": "E1"})}
    two = {"data": [True, False, None, 1.5, {"label": "E1"}], "schema_version": 1}
    assert canonical_job_payload(one) == canonical_job_payload(two)


@pytest.mark.parametrize(
    "changes",
    [
        {"status": "lost"},
        {"revision": True},
        {"revision": 0},
        {"title": " "},
        {"title": "x" * 301},
        {"title": "line\nbreak"},
        {"stage": "Unsafe stage"},
        {"error": "Exception: sensitive provider text"},
        {"updated_at": NOW - timedelta(seconds=1)},
        {"created_at": NOW.replace(tzinfo=None)},
        {"lease_token": uuid4()},
        {"lease_until": NOW},
        {"status": "running"},
        {"lease_token": uuid4(), "lease_until": NOW},
        {"status": "running", "lease_token": uuid4(), "lease_until": NOW.replace(tzinfo=None)},
    ],
)
def test_job_record_rejects_invalid_state(changes):
    with pytest.raises(ValueError):
        job(**changes)


@pytest.mark.parametrize("seconds", [0, -1, 3601])
def test_lease_has_a_bounded_positive_lifetime(seconds):
    with pytest.raises(ValueError):
        job_lease(NOW, NOW + timedelta(seconds=seconds))


@pytest.mark.parametrize(
    "payload",
    ['{"schema_version":2}', '{"schema_version":1,"schema_version":1}', '{"schema_version":1'],
)
async def test_valid_storage_hash_does_not_bypass_json_schema_or_encoding(job_storage, payload):
    _, factory = job_storage
    value = await saved(factory, job())
    encoded = payload.encode()
    async with factory() as session:
        await session.execute(
            update(ReportJobRow)
            .where(ReportJobRow.id == value.id)
            .values(
                payload=payload,
                payload_bytes=len(encoded),
                payload_sha256=hashlib.sha256(encoded).hexdigest(),
            )
        )
        await session.commit()
        with pytest.raises(Conflict):
            await SqlReportJobRepository(session).get(value.id)


async def test_failed_or_paused_checkpoint_can_resume_but_expired_worker_cannot_write(job_storage):
    _, factory = job_storage
    for state in ("failed", "paused"):
        value = await saved(factory, job())
        token = uuid4()
        async with factory() as session:
            repository = SqlReportJobRepository(session)
            await repository.claim(
                value.id,
                expected_revision=1,
                lease_token=token,
                now=NOW,
                lease_until=NOW + timedelta(seconds=10),
            )
            assert (
                await repository.checkpoint(
                    value.id,
                    expected_revision=2,
                    lease_token=token,
                    payload=value.payload,
                    stage="late",
                    now=NOW + timedelta(seconds=10),
                )
                is None
            )
            current = await repository.checkpoint(
                value.id,
                expected_revision=2,
                lease_token=token,
                payload=value.payload,
                stage="drafting",
                now=NOW,
                status=state,
                error="provider_failed",
            )
            assert current.status == state and current.lease_token is current.lease_until is None
            assert await repository.count_active(value.owner_id) == 0
            assert await repository.count_open(value.owner_id) == 1
            resumed = await repository.resume(value.id, expected_revision=current.revision, now=NOW)
            assert resumed.payload == value.payload and resumed.error is None
            await session.commit()


async def test_queries_and_mutations_reject_invalid_control_inputs(job_storage):
    _, factory = job_storage
    value = await saved(factory, job())
    async with factory() as session:
        repository = SqlReportJobRepository(session)
        assert await repository.get(uuid4()) is None
        with pytest.raises(ValueError):
            await repository.queued(101)
        with pytest.raises(ValueError):
            await repository.pause(value.id, expected_revision=True, now=NOW)
        with pytest.raises(ValueError):
            await repository.pause(value.id, expected_revision=1, now=NOW, error="bad error")
        with pytest.raises(ValueError):
            await repository.checkpoint(
                value.id,
                expected_revision=1,
                lease_token=uuid4(),
                payload=value.payload,
                stage="done",
                now=NOW,
                status="completed",
            )
        assert (
            await repository.claim(
                value.id,
                expected_revision=1,
                lease_token=uuid4(),
                now=NOW - timedelta(seconds=1),
                lease_until=NOW,
            )
            is None
        )


async def test_predetermined_final_version_identifier_is_unique(job_storage):
    _, factory = job_storage
    value = await saved(factory, job())
    async with factory() as session:
        with pytest.raises(IntegrityError):
            await SqlReportJobRepository(session).add(replace(job(), version_id=value.version_id))
        await session.rollback()


async def test_resume_atomically_replaces_only_expected_paused_revision(job_storage):
    _, factory = job_storage
    original = {
        "schema_version": 1,
        "sections": {"done": "Frozen"},
        "calls": [{"status": "in_flight"}],
    }
    value = await saved(factory, job(status="paused", payload=original))
    resumed_payload = {**original, "calls": [{"status": "uncertain"}]}
    async with factory() as session:
        repository = SqlReportJobRepository(session)
        assert (
            await repository.resume(value.id, expected_revision=2, now=NOW, payload=resumed_payload)
            is None
        )
        assert (await repository.get(value.id)).payload == original
        resumed = await repository.resume(
            value.id, expected_revision=1, now=NOW, payload=resumed_payload
        )
        assert resumed.status == "queued" and resumed.payload == resumed_payload
        await session.commit()
    async with factory() as session:
        assert (await SqlReportJobRepository(session).get(value.id)).payload == resumed_payload
