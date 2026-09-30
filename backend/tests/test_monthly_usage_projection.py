"""Generated audit-ledger parity and fail-closed malformed receipt handling."""

from datetime import timedelta
from uuid import uuid4

import pytest

from ase.adapters.persistence.models import LlmUsageRow
from ase.adapters.persistence.monthly_report_usage import monthly_usage
from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.application.report_jobs.budget import MAX_COUNTER, JobInterrupted
from report_job_helpers import NOW, job, saved
from report_job_helpers import job_storage as _job_storage  # noqa: F401
from report_usage_reference import legacy_monthly_usage


async def test_generated_jobs_preserve_legacy_month_totals(job_storage):
    _, factory = job_storage
    owners = [uuid4(), uuid4()]
    variants = [
        {"status": "in_flight"},
        {"status": "uncertain"},
        {"status": "completed", "completion_tokens": 17},
        {"status": "completed", "completion_tokens": None},
        {"status": "failed", "completion_tokens": 0, "error": "not_dispatched"},
        {"status": "failed", "completion_tokens": None},
        {"status": "failed", "completion_tokens": 7},
    ]
    for index in range(50):
        created = NOW - timedelta(days=35)
        calls = [
            dict(
                variant,
                reserved_output=100 + index,
                dispatched_at=(NOW + timedelta(days=offset)).isoformat(),
            )
            for offset in (-31, 0, 31)
            for variant in variants
        ]
        await saved(
            factory,
            job(
                owner_id=owners[index % 2],
                created_at=created,
                updated_at=NOW + timedelta(days=31),
                payload={"schema_version": 1, "calls": calls},
            ),
        )
    async with factory() as session:
        for owner in owners:
            session.add(
                LlmUsageRow(
                    at=NOW,
                    profile_id=uuid4(),
                    user_id=owner,
                    purpose="report-job",
                    ok=True,
                    latency_ms=1,
                    completion_tokens=123,
                )
            )
        await session.commit()
        for owner in owners:
            for at in (NOW - timedelta(days=31), NOW, NOW + timedelta(days=31)):
                assert await monthly_usage(session, owner, None, at) == await legacy_monthly_usage(
                    session, owner, None, at
                )


@pytest.mark.parametrize("completion", [-1, MAX_COUNTER + 1, 1.5, "invalid"])
async def test_invalid_receipt_still_blocks_monthly_budget(job_storage, completion):
    _, factory = job_storage
    owner = uuid4()
    async with factory() as session:
        session.add(
            LlmUsageRow(
                at=NOW,
                profile_id=uuid4(),
                user_id=owner,
                purpose="report-job",
                ok=True,
                latency_ms=1,
                completion_tokens=completion,
            )
        )
        await session.commit()
        with pytest.raises(JobInterrupted):
            await monthly_usage(session, owner, None, NOW)


async def test_discard_removes_projected_reservations_with_job(job_storage):
    _, factory = job_storage
    value = await saved(
        factory,
        job(
            status="paused",
            payload={
                "schema_version": 1,
                "calls": [{"status": "uncertain", "reserved_output": 100}],
            },
        ),
    )
    async with factory() as session:
        assert (await monthly_usage(session, value.owner_id, None, NOW))[0].requests == 1
        assert await SqlReportJobRepository(session).discard(value.id, expected_revision=1)
        await session.commit()
        assert (await monthly_usage(session, value.owner_id, None, NOW))[0].requests == 0
