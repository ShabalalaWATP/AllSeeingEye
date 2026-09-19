"""Durable ownership, lease fencing and transaction semantics, without provider calls."""

import asyncio
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import event, inspect, update
from sqlalchemy.exc import IntegrityError

from ase.adapters.persistence.report_job_models import ReportJobRow
from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.domain.access import Visibility
from ase.domain.errors import Conflict
from report_job_helpers import NOW, job, saved
from report_job_helpers import job_storage as _job_storage  # noqa: F401


async def test_frozen_checkpoint_survives_new_session_and_is_independent_of_caller(job_storage):
    _, factory = job_storage
    value = job(payload={"schema_version": 1, "evidence": [{"label": "E1", "title": "Original"}]})
    await saved(factory, value)
    value.payload["evidence"][0]["title"] = "Changed in memory"
    async with factory() as session:
        restored = await SqlReportJobRepository(session).get(value.id)
        assert restored.payload["evidence"][0]["title"] == "Original"
        assert restored.report_id == value.report_id and restored.version_id == value.version_id
        assert restored.created_at == NOW


async def test_idempotency_is_unique_per_owner_and_never_crosses_owner(job_storage):
    _, factory = job_storage
    first = await saved(factory, job())
    other = await saved(factory, job(request_key=first.request_key))
    async with factory() as session:
        repository = SqlReportJobRepository(session)
        assert (await repository.get_by_request(first.owner_id, first.request_key)).id == first.id
        assert (await repository.get_by_request(other.owner_id, first.request_key)).id == other.id
        assert await repository.get_by_request(uuid4(), first.request_key) is None
        with pytest.raises(IntegrityError):
            await repository.add(job(owner_id=first.owner_id, request_key=first.request_key))
        await session.rollback()


async def test_two_workers_cannot_claim_the_same_revision(job_storage):
    _, factory = job_storage
    value = await saved(factory, job())

    async def claim():
        async with factory() as session:
            claimed = await SqlReportJobRepository(session).claim(
                value.id,
                expected_revision=1,
                lease_token=uuid4(),
                now=NOW,
                lease_until=NOW + timedelta(minutes=5),
            )
            await session.commit()
            return claimed

    results = await asyncio.gather(claim(), claim())
    assert sum(result is not None for result in results) == 1
    assert next(result for result in results if result).revision == 2


async def test_two_workers_cannot_claim_distinct_jobs_for_one_owner(job_storage):
    _, factory = job_storage
    owner = uuid4()
    values = [await saved(factory, job(owner_id=owner)) for _ in range(2)]

    async def claim(value):
        async with factory() as session:
            claimed = await SqlReportJobRepository(session).claim(
                value.id,
                expected_revision=1,
                lease_token=uuid4(),
                now=NOW,
                lease_until=NOW + timedelta(minutes=5),
            )
            await session.commit()
            return claimed

    results = await asyncio.gather(*(claim(value) for value in values))
    assert sum(result is not None for result in results) == 1


async def test_pause_resume_revokes_old_worker_and_preserves_completed_sections(job_storage):
    _, factory = job_storage
    value = await saved(factory, job())
    first, replacement = uuid4(), uuid4()
    payload = {"schema_version": 1, "sections": {"summary": {"text": "Saved", "citations": ["E1"]}}}
    async with factory() as session:
        repository = SqlReportJobRepository(session)
        claimed = await repository.claim(
            value.id,
            expected_revision=1,
            lease_token=first,
            now=NOW,
            lease_until=NOW + timedelta(minutes=5),
        )
        checkpoint = await repository.checkpoint(
            value.id,
            expected_revision=claimed.revision,
            lease_token=first,
            payload=payload,
            stage="drafting:summary",
            now=NOW,
            lease_until=NOW + timedelta(minutes=10),
        )
        assert checkpoint.lease_until == NOW + timedelta(minutes=10)
        paused = await repository.pause(value.id, expected_revision=checkpoint.revision, now=NOW)
        resumed = await repository.resume(value.id, expected_revision=paused.revision, now=NOW)
        current = await repository.claim(
            value.id,
            expected_revision=resumed.revision,
            lease_token=replacement,
            now=NOW,
            lease_until=NOW + timedelta(minutes=5),
        )
        assert current.payload == payload
        for revision in (checkpoint.revision, current.revision):
            assert (
                await repository.checkpoint(
                    value.id,
                    expected_revision=revision,
                    lease_token=first,
                    payload={"schema_version": 1},
                    stage="late",
                    now=NOW,
                )
                is None
            )
            assert (
                await repository.complete(
                    value.id,
                    expected_revision=revision,
                    lease_token=first,
                    payload=payload,
                    now=NOW,
                )
                is None
            )
        await session.commit()


async def test_expired_running_work_pauses_without_automatic_paid_retry(job_storage):
    _, factory = job_storage
    values = [await saved(factory, job()) for _ in range(3)]
    async with factory() as session:
        repository = SqlReportJobRepository(session)
        for value in values:
            await repository.claim(
                value.id,
                expected_revision=1,
                lease_token=uuid4(),
                now=NOW,
                lease_until=NOW + timedelta(seconds=10),
            )
        await session.commit()
    async with factory() as session:
        repository = SqlReportJobRepository(session)
        assert await repository.recover_expired(NOW + timedelta(seconds=9)) == 0
        assert await repository.recover_expired(NOW + timedelta(seconds=10), limit=2) == 2
        assert await repository.recover_expired(NOW + timedelta(seconds=10)) == 1
        assert await repository.queued() == []
        for value in values:
            recovered = await repository.get(value.id)
            assert recovered.status == "paused" and recovered.error == "interrupted_uncertain"
            assert recovered.lease_token is recovered.lease_until is None
        await session.commit()


async def test_queue_interleaves_owners_before_one_owner_can_fill_the_page(job_storage):
    _, factory = job_storage
    first_owner, second_owner = uuid4(), uuid4()
    first = await saved(factory, job(owner_id=first_owner, created_at=NOW))
    await saved(
        factory,
        job(
            owner_id=first_owner,
            created_at=NOW + timedelta(seconds=1),
            updated_at=NOW + timedelta(seconds=1),
        ),
    )
    second = await saved(
        factory,
        job(
            owner_id=second_owner,
            created_at=NOW + timedelta(seconds=2),
            updated_at=NOW + timedelta(seconds=2),
        ),
    )
    async with factory() as session:
        queued = await SqlReportJobRepository(session).queued(limit=2)
    assert queued == [first.id, second.id]


async def test_running_owner_cannot_claim_second_slot_when_another_owner_arrives(job_storage):
    _, factory = job_storage
    owner, other_owner = uuid4(), uuid4()
    first = await saved(factory, job(owner_id=owner, created_at=NOW))
    sibling = await saved(
        factory,
        job(
            owner_id=owner,
            created_at=NOW + timedelta(seconds=1),
            updated_at=NOW + timedelta(seconds=1),
        ),
    )
    async with factory() as session:
        repository = SqlReportJobRepository(session)
        assert await repository.claim(
            first.id,
            expected_revision=1,
            lease_token=uuid4(),
            now=NOW,
            lease_until=NOW + timedelta(minutes=5),
        )
        await session.commit()
    other = await saved(
        factory,
        job(
            owner_id=other_owner,
            created_at=NOW + timedelta(seconds=2),
            updated_at=NOW + timedelta(seconds=2),
        ),
    )
    async with factory() as session:
        repository = SqlReportJobRepository(session)
        assert await repository.queued(limit=2) == [other.id]
        assert (
            await repository.claim(
                sibling.id,
                expected_revision=1,
                lease_token=uuid4(),
                now=NOW,
                lease_until=NOW + timedelta(minutes=5),
            )
            is None
        )


@pytest.mark.parametrize("needs_review", [False, True])
async def test_completion_and_rollback_belong_to_callers_transaction(job_storage, needs_review):
    _, factory = job_storage
    value = await saved(factory, job())
    token = uuid4()
    async with factory() as session:
        repository = SqlReportJobRepository(session)
        await repository.claim(
            value.id,
            expected_revision=1,
            lease_token=token,
            now=NOW,
            lease_until=NOW + timedelta(minutes=5),
        )
        await session.commit()
        final = await repository.complete(
            value.id,
            expected_revision=2,
            lease_token=token,
            payload=value.payload,
            now=NOW,
            needs_review=needs_review,
        )
        assert final.status == ("needs_review" if needs_review else "completed")
        await session.rollback()
        assert (await repository.get(value.id)).status == "running"
        final = await repository.complete(
            value.id,
            expected_revision=2,
            lease_token=token,
            payload=value.payload,
            now=NOW,
            needs_review=needs_review,
        )
        await session.commit()
        assert await repository.resume(value.id, expected_revision=final.revision, now=NOW) is None
        assert await repository.pause(value.id, expected_revision=final.revision, now=NOW) is None
        assert await repository.count_open() == await repository.count_active() == 0


async def test_visibility_filters_before_limit_and_lists_never_load_frozen_evidence(job_storage):
    engine, factory = job_storage
    owner, stranger, team = uuid4(), uuid4(), uuid4()
    personal = await saved(
        factory,
        job(
            owner_id=owner,
            payload={
                "schema_version": 1,
                "summary": {"completed_sections": 2},
                "evidence": ["x" * 500_000],
            },
        ),
    )
    team_job = await saved(factory, job(owner_id=stranger, team_id=team))
    await saved(
        factory,
        job(
            owner_id=stranger,
            created_at=NOW + timedelta(seconds=1),
            updated_at=NOW + timedelta(seconds=1),
        ),
    )
    statements = []

    def capture(_connection, _cursor, statement, _parameters, _context, _many):
        statements.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", capture)
    try:
        async with factory() as session:
            repository = SqlReportJobRepository(session)
            rows = await repository.list_visible(Visibility(owner, False, ()), limit=1)
            assert rows[0].id == personal.id
            assert rows[0].payload == {"schema_version": 1, "summary": {"completed_sections": 2}}
            assert len(statements) == 1 and "json_extract" in statements[0]
            assert all(
                "payload" in inspect(value).unloaded for value in session.identity_map.values()
            )
            rows = await repository.list_visible(Visibility(owner, False, (team,)))
            assert {row.id for row in rows} == {personal.id, team_job.id}
            assert len(await repository.list_visible(Visibility(owner, True, ()))) == 3
            assert await repository.count_active(owner) == await repository.count_open(owner) == 1
            assert await repository.count_active() == await repository.count_open() == 3
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", capture)


async def test_corrupt_payload_cannot_be_read_as_a_valid_checkpoint(job_storage):
    _, factory = job_storage
    value = await saved(factory, job())
    async with factory() as session:
        await session.execute(
            update(ReportJobRow)
            .where(ReportJobRow.id == value.id)
            .values(payload='{"schema_version":1,"changed":true}')
        )
        await session.commit()
        with pytest.raises(Conflict):
            await SqlReportJobRepository(session).get(value.id)
