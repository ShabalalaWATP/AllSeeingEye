"""Checkpoint observations cannot share the worker's uncommitted SQL transaction."""

from sqlalchemy import text

from report_job_api_helpers import work  # noqa: F401, marks a report-worker test module


async def test_checkpoint_reader_does_not_see_or_rollback_uncommitted_worker_write(container):
    async with container.engine.begin() as connection:
        await connection.execute(text("CREATE TABLE test_job_checkpoint (value INTEGER)"))
    try:
        async with container.session_factory() as writer:
            await writer.execute(text("INSERT INTO test_job_checkpoint (value) VALUES (1)"))
            async with container.session_factory() as reader:
                pending = await reader.scalar(text("SELECT COUNT(*) FROM test_job_checkpoint"))
            await writer.commit()
        async with container.session_factory() as reader:
            committed = await reader.scalar(text("SELECT COUNT(*) FROM test_job_checkpoint"))
        assert (pending, committed) == (0, 1), "Checkpoint reads must use a separate transaction"
    finally:
        async with container.engine.begin() as connection:
            await connection.execute(text("DROP TABLE test_job_checkpoint"))
