"""Native clones keep mutation rejection and post-acquisition schema fallback."""

import pytest
from sqlalchemy import inspect

from ase.adapters.persistence.base import Base
from ase.adapters.persistence.session import create_engine
from test_postgres_template_postgres import worker as worker  # noqa: PLC0414

pytestmark = pytest.mark.postgres


async def test_cold_seal_mutation_rejects_clone_and_keeps_template_owned(worker, monkeypatch):
    original = worker._command
    column = Base.metadata.tables["users"].c.display_name

    async def command(name, **kwargs):
        await original(name, **kwargs)
        if kwargs.get("seal"):
            monkeypatch.setattr(column, "nullable", not column.nullable)

    monkeypatch.setattr(worker, "_command", command)
    assert await worker.acquire() is None
    assert worker._created == {worker.template}
    assert len(worker._allocated) == 1 and not worker._leases


async def test_warm_metadata_change_rejects_before_native_clone(worker, monkeypatch):
    first = await worker.acquire()
    assert first is not None
    await worker.release(first)
    allocated = set(worker._allocated)
    column = Base.metadata.tables["users"].c.display_name
    monkeypatch.setattr(column, "nullable", not column.nullable)
    assert await worker.acquire() is None
    assert worker._allocated == allocated
    assert worker._created == {worker.template} and not worker._leases


async def test_change_during_native_clone_is_rechecked_by_prepare_and_teardown(worker, monkeypatch):
    first = await worker.acquire()
    assert first is not None
    await worker.release(first)
    original = worker._command
    column = Base.metadata.tables["users"].c.display_name
    assert not column.nullable

    async def command(name, **kwargs):
        await original(name, **kwargs)
        if kwargs.get("clone"):
            monkeypatch.setattr(column, "nullable", True)

    monkeypatch.setattr(worker, "_command", command)
    database = await worker.acquire()
    assert database is not None
    engine = create_engine(database.url)

    async def nullable():
        async with engine.connect() as connection:
            columns = await connection.run_sync(lambda sync: inspect(sync).get_columns("users"))
            return next(value["nullable"] for value in columns if value["name"] == "display_name")

    try:
        assert await nullable() is False  # Clone still has the sealed original schema.
        await database.prepare(engine)
        assert database.reset and await nullable() is True
        assert database.requires_drop(engine)
        monkeypatch.setattr(column, "nullable", False)
        assert database.requires_drop(engine)  # Once reset, teardown remains mandatory.
    finally:
        await engine.dispose()
        await worker.release(database)
