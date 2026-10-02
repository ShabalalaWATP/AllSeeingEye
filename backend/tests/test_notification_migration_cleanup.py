"""A cancelled migration cannot release its database while Alembic still uses it."""

import asyncio
from threading import Event

import pytest
from alembic import command

from notification_migration_helpers import MigrationDatabase


@pytest.mark.parametrize("downgrade", [False, True])
@pytest.mark.parametrize("cancellations", [1, 2])
async def test_cancelled_migration_joins_its_thread_before_database_cleanup(
    monkeypatch, downgrade, cancellations
):
    started, release, finished = Event(), Event(), Event()

    def migration(_config, _revision):
        started.set()
        try:
            assert release.wait(timeout=5), "The test did not release its migration thread"
        finally:
            finished.set()

    monkeypatch.setattr(command, "downgrade" if downgrade else "upgrade", migration)
    database = MigrationDatabase("sqlite+aiosqlite://")
    task = asyncio.create_task(database.migrate("head", downgrade=downgrade))
    try:
        assert await asyncio.to_thread(started.wait, 5)
        for _ in range(cancellations):
            task.cancel()
            await asyncio.sleep(0)
        # Returning here would let a fixture drop its database under Alembic.
        assert not task.done()
        assert not finished.is_set()
    finally:
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert await asyncio.to_thread(finished.wait, 5)
    assert finished.is_set()
