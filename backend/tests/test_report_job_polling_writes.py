"""Compact polling projections follow checkpoint writes and transaction boundaries."""

import hashlib
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import select

from ase.adapters.persistence.report_job_models import ReportJobRow
from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.domain.access import Visibility
from ase.domain.report_jobs import canonical_job_payload
from report_job_helpers import NOW, job, saved
from report_job_helpers import job_storage as _job_storage  # noqa: F401


def payload(origin):
    return {
        "schema_version": 1,
        "input": {"scope": {"origin": origin}},
        "summary": {"completed_sections": 1, "nested": {"count": 1}},
    }


async def assert_projection(session, expected):
    row = await session.scalar(
        select(ReportJobRow)
        .where(ReportJobRow.id == expected.id)
        .execution_options(populate_existing=True)
    )
    encoded = canonical_job_payload(expected.payload)
    assert row.payload.encode() == encoded
    assert row.payload_sha256 == hashlib.sha256(encoded).hexdigest()
    assert row.payload_bytes == len(encoded)
    origin = expected.payload["input"]["scope"]["origin"]
    assert row.summary == {**expected.payload["summary"], "origin": origin}
    listed = await SqlReportJobRepository(session).list_page(
        Visibility(expected.owner_id, False, ()), limit=1, include_briefings=True
    )
    assert listed[0].payload == {"schema_version": 1, "summary": row.summary}
    listed[0].payload["summary"]["nested"]["count"] = 99
    assert row.summary["nested"]["count"] == 1


async def test_each_checkpoint_replacement_updates_projection_atomically(job_storage):
    _, factory = job_storage
    value = await saved(factory, job(payload=payload("research")))
    async with factory() as session:
        repository = SqlReportJobRepository(session)
        await assert_projection(session, value)
        token = uuid4()
        running = await repository.claim(
            value.id,
            expected_revision=1,
            lease_token=token,
            now=NOW,
            lease_until=NOW + timedelta(seconds=30),
        )
        await session.commit()
        await assert_projection(session, running)

        changed = await repository.checkpoint(
            value.id,
            expected_revision=running.revision,
            lease_token=token,
            payload=payload("briefing"),
            stage="drafting",
            now=NOW,
            status="paused",
        )
        await assert_projection(session, changed)
        await session.rollback()
        await assert_projection(session, running)

        changed = await repository.checkpoint(
            value.id,
            expected_revision=running.revision,
            lease_token=token,
            payload=payload("briefing"),
            stage="drafting",
            now=NOW,
            status="paused",
        )
        await session.commit()
        await assert_projection(session, changed)
        assert (
            await repository.resume(
                value.id, expected_revision=1, now=NOW, payload=payload("research")
            )
            is None
        )
        await assert_projection(session, changed)
        resumed = await repository.resume(
            value.id, expected_revision=changed.revision, now=NOW, payload=payload("subscription")
        )
        await assert_projection(session, resumed)
        running = await repository.claim(
            value.id,
            expected_revision=resumed.revision,
            lease_token=token,
            now=NOW,
            lease_until=NOW + timedelta(seconds=30),
        )
        completed = await repository.complete(
            value.id,
            expected_revision=running.revision,
            lease_token=token,
            payload=payload("geolocation"),
            now=NOW,
        )
        await session.commit()
        await assert_projection(session, completed)


async def test_lease_recovery_preserves_origin_and_original_checkpoint(job_storage):
    _, factory = job_storage
    value = await saved(
        factory,
        job(
            payload=payload("briefing"),
            status="running",
            lease_token=uuid4(),
            lease_until=NOW + timedelta(seconds=1),
        ),
    )
    async with factory() as session:
        repository = SqlReportJobRepository(session)
        assert await repository.recover_expired(NOW + timedelta(seconds=2)) == 1
        await session.commit()
        recovered = await repository.get(value.id)
        assert recovered.payload == value.payload and recovered.status == "paused"
        await assert_projection(session, recovered)
        assert await repository.list_page(Visibility(value.owner_id, False, ()), limit=1) == []
