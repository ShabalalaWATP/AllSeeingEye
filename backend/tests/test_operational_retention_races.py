"""Independent maintenance processes serialise bounded work without double deletion."""

import asyncio
from datetime import timedelta

from ase.adapters.persistence.models import AuditLogRow
from ase.adapters.persistence.users import SqlUserRepository
from operational_retention_helpers import audit, count, run, seed
from token_race_helpers import race_container as race_container  # noqa: PLC0414


async def test_two_processes_drain_distinct_bounded_batches(race_container, monkeypatch):
    container = race_container
    await seed(container, *(audit(container.clock.now() - timedelta(days=366)) for _ in range(205)))
    first_locked, second_waiting, release_first = asyncio.Event(), asyncio.Event(), asyncio.Event()
    connections = {}
    original = SqlUserRepository.lock_administration

    async def guarded(repository):
        task = asyncio.current_task().get_name()
        connection = await repository._session.connection()
        connections[task] = id(connection.sync_connection.connection.dbapi_connection)
        if task == "second-maintenance":
            second_waiting.set()
        await original(repository)
        if task == "first-maintenance":
            first_locked.set()
            await asyncio.wait_for(release_first.wait(), 10)

    monkeypatch.setattr(SqlUserRepository, "lock_administration", guarded)
    first = asyncio.create_task(run(container), name="first-maintenance")
    second = None
    try:
        await asyncio.wait_for(first_locked.wait(), 10)
        second = asyncio.create_task(run(container), name="second-maintenance")
        await asyncio.wait_for(second_waiting.wait(), 10)
        release_first.set()
        results = await asyncio.wait_for(asyncio.gather(first, second), 10)
        assert [result["audit"] for result in results] == [100, 100]
        assert await count(container, AuditLogRow) == 5
        assert len(set(connections.values())) == 2
    finally:
        release_first.set()
        tasks = [first, *([second] if second else [])]
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
