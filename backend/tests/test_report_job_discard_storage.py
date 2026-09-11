"""Explicit inactive-job cleanup fences revisions and never touches active work."""

from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import event

from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from report_job_helpers import NOW, job, saved
from report_job_helpers import job_storage as _job_storage  # noqa: F401


@pytest.mark.parametrize("status", ["paused", "failed", "completed", "needs_review"])
async def test_discard_is_revision_fenced_and_caller_committed(job_storage, status):
    engine, factory = job_storage
    stored = await saved(factory, job(status=status))
    statements = []

    def capture(_connection, _cursor, statement, _parameters, _context, _many):
        statements.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", capture)
    try:
        async with factory() as session:
            repository = SqlReportJobRepository(session)
            assert not await repository.discard(stored.id, expected_revision=2)
            assert await repository.discard(stored.id, expected_revision=1)
            await session.rollback()
            assert await repository.get(stored.id) is not None
            assert await repository.discard(stored.id, expected_revision=1)
            await session.commit()
        async with factory() as session:
            repository = SqlReportJobRepository(session)
            assert await repository.get(stored.id) is None
            assert not await repository.discard(stored.id, expected_revision=1)
        deletions = [statement for statement in statements if statement.startswith("DELETE")]
        assert deletions and all(
            statement.startswith("DELETE FROM report_jobs ") for statement in deletions
        )
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", capture)


@pytest.mark.parametrize("status", ["queued", "running"])
async def test_discard_never_deletes_active_work(job_storage, status):
    _, factory = job_storage
    lease = (
        {}
        if status == "queued"
        else {"lease_token": uuid4(), "lease_until": NOW + timedelta(seconds=45)}
    )
    stored = await saved(factory, job(status=status, **lease))
    async with factory() as session:
        repository = SqlReportJobRepository(session)
        assert not await repository.discard(stored.id, expected_revision=1)
        assert (await repository.get(stored.id)).status == status
        with pytest.raises(ValueError):
            await repository.discard(stored.id, expected_revision=True)
