"""Known drafting failures survive lease expiry without weakening ownership fences."""

from copy import deepcopy
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.application.report_jobs.recovery import expired_failure
from ase.application.reports.drafting import Draft
from ase.application.reports.sections import SectionIncomplete
from ase.container.report_job_worker import ReportJobWorker
from report_job_helpers import NOW, job, saved
from report_job_helpers import job_storage as _job_storage  # noqa: F401

DIGEST = "a" * 64


def known_failure_payload():
    return {
        "schema_version": 1,
        "current_packet": DIGEST,
        "stage": "drafting",
        "calls": [{"status": "completed", "error": None}],
        "sections": {
            f"{DIGEST}:S2": {
                "packet_digest": DIGEST,
                "section_id": "S2",
                "status": "incomplete",
                "reason": "invalid_section",
                "payload": {"id": "S2", "kind": "topic"},
            },
        },
    }


async def test_known_worker_failure_can_pause_its_own_expired_lease(job_storage, monkeypatch):
    _, factory = job_storage
    original = await saved(
        factory,
        job(
            status="running",
            lease_token=uuid4(),
            lease_until=NOW + timedelta(seconds=45),
            payload=known_failure_payload(),
        ),
    )
    container = SimpleNamespace(
        session_factory=factory, clock=SimpleNamespace(now=lambda: NOW + timedelta(seconds=46))
    )
    monkeypatch.setattr(
        "ase.container.report_job_worker.execute_job",
        AsyncMock(side_effect=SectionIncomplete("S2", "invalid_section", Draft())),
    )
    await ReportJobWorker(container).process(original)
    async with factory() as session:
        repo = SqlReportJobRepository(session)
        current = await repo.get(original.id)
        assert current.status == "paused"
        assert current.error == "section_invalid_section"
        assert current.lease_token is None
        assert current.payload == original.payload
        assert await repo.recover_expired(NOW + timedelta(minutes=2)) == 0


@pytest.mark.parametrize("status", ["paused", "failed"])
async def test_terminal_checkpoint_preserves_token_revision_and_running_fences(job_storage, status):
    _, factory = job_storage
    original = await saved(
        factory,
        job(status="running", lease_token=uuid4(), lease_until=NOW + timedelta(seconds=1)),
    )
    now = NOW + timedelta(seconds=2)
    async with factory() as session:
        repo = SqlReportJobRepository(session)
        args = {
            "expected_revision": original.revision,
            "lease_token": original.lease_token,
            "payload": original.payload,
            "stage": "paused",
            "now": now,
            "status": status,
        }
        assert await repo.checkpoint(original.id, **(args | {"lease_token": uuid4()})) is None
        assert await repo.checkpoint(original.id, **(args | {"expected_revision": 2})) is None
        assert await repo.checkpoint(original.id, **(args | {"status": "running"})) is None
        assert (
            await repo.complete(
                original.id,
                expected_revision=original.revision,
                lease_token=original.lease_token,
                payload=original.payload,
                now=now,
            )
            is None
        )
        stopped = await repo.checkpoint(original.id, **args)
        assert stopped is not None and stopped.status == status
        assert (
            await repo.checkpoint(original.id, **(args | {"expected_revision": stopped.revision}))
            is None
        )


@pytest.mark.parametrize(
    "uncertainty",
    [
        None,
        "in_flight",
        "uncertain",
        "failed",
        "running_section",
        "other_packet",
        "unknown_reason",
        "ambiguous_reason",
        "mismatched_identity",
        "malformed_calls",
    ],
)
async def test_expired_recovery_preserves_only_proven_current_failure(job_storage, uncertainty):
    _, factory = job_storage
    payload = known_failure_payload()
    section = payload["sections"][f"{DIGEST}:S2"]
    if uncertainty in {"in_flight", "uncertain", "failed"}:
        payload["calls"][0]["status"] = uncertainty
    elif uncertainty == "running_section":
        payload["sections"][f"{DIGEST}:S3"] = {"status": "running"}
    elif uncertainty == "other_packet":
        payload["current_packet"] = "b" * 64
    elif uncertainty == "unknown_reason":
        section["reason"] = "untrusted_reason"
    elif uncertainty == "ambiguous_reason":
        other = deepcopy(section)
        other.update(
            section_id="S3", reason="invalid_synthesis", payload={"id": "S3", "kind": "topic"}
        )
        payload["sections"][f"{DIGEST}:S3"] = other
    elif uncertainty == "mismatched_identity":
        section["section_id"] = "different"
    elif uncertainty == "malformed_calls":
        payload["calls"] = [None]
    original = await saved(
        factory,
        job(
            status="running",
            lease_token=uuid4(),
            lease_until=NOW + timedelta(seconds=1),
            payload=payload,
        ),
    )
    async with factory() as session:
        repo = SqlReportJobRepository(session)
        assert await repo.recover_expired(NOW + timedelta(seconds=2)) == 1
        recovered = await repo.get(original.id)
        assert recovered.status == "paused"
        assert recovered.error == (
            "section_invalid_section" if uncertainty is None else "interrupted_uncertain"
        )
        assert recovered.payload == payload
        assert await repo.queued() == []


@pytest.mark.parametrize(
    "changes",
    [
        {"calls": []},
        {"calls": {"status": "completed"}},
        {"calls": [{"status": "completed", "error": "interrupted"}]},
        {"current_packet": "invalid"},
        {"current_packet": None},
        {"sections": []},
        {"sections": {"unknown": None}},
        {"sections": {"unknown": {"status": "unknown"}}},
    ],
)
def test_incomplete_recovery_metadata_keeps_uncertainty(changes):
    assert expired_failure(known_failure_payload() | changes) == "interrupted_uncertain"


def test_invalid_or_missing_section_body_cannot_prove_a_current_failure():
    payload = known_failure_payload()
    section = payload["sections"][f"{DIGEST}:S2"]
    for body in (None, {"id": "another", "kind": "topic"}, {"id": "S2", "kind": []}):
        section["payload"] = body
        assert expired_failure(payload) == "interrupted_uncertain"
