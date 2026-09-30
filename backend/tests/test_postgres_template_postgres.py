"""Real owned PostgreSQL template copies, transaction isolation and cleanup failures."""

import os
from types import SimpleNamespace
from uuid import uuid4

import asyncpg
import pytest
from sqlalchemy import event, inspect, text
from sqlalchemy.engine import make_url

import conftest
from ase.adapters.persistence.base import Base
from ase.adapters.persistence.session import create_engine
from postgres_isolation import database_command, worker_database_url
from postgres_template_guard import schema_fingerprint
from postgres_template_store import TemplateWorker
from pytest_support import drop_schema


@pytest.fixture
async def worker():
    service = os.environ.get("ASE_TEMPLATE_TEST_POSTGRES_URL") or os.environ.get(
        "ASE_TEST_DATABASE_URL"
    )
    if not service:
        pytest.skip("Requires an explicitly owned local template-test PostgreSQL service")
    parsed = make_url(service)
    assert not parsed.query
    private = worker_database_url(service, "master", uuid4().hex)
    await database_command(service, private, create=True)
    pool = TemplateWorker(private, schema_fingerprint())
    try:
        yield pool
    finally:
        try:
            await pool.close()
            connection = await asyncpg.connect(private.replace("+asyncpg", ""))
            try:
                remaining = await connection.fetchval(
                    "SELECT count(*) FROM pg_database WHERE datname = ANY($1::text[])",
                    list(pool._allocated),
                )
                assert remaining == 0
            finally:
                await connection.close()
        finally:
            await database_command(service, private, create=False)


async def test_clones_are_empty_independent_and_template_rejects_connections(worker):
    first, second = await worker.acquire(), await worker.acquire()
    assert first and second and first.name != second.name
    first_engine, second_engine = create_engine(first.url), create_engine(second.url)
    try:
        async with first_engine.connect() as writer, first_engine.connect() as reader:
            tables = await writer.run_sync(lambda sync: inspect(sync).get_table_names())
            assert set(tables) == set(Base.metadata.tables)
            await writer.execute(text("INSERT INTO administration_lock DEFAULT VALUES"))
            assert await reader.scalar(text("SELECT count(*) FROM administration_lock")) == 0
            await reader.rollback()
            await writer.commit()
            assert await reader.scalar(text("SELECT id FROM administration_lock")) == 1
            await reader.rollback()
            await writer.execute(text("INSERT INTO administration_lock DEFAULT VALUES"))
            await writer.rollback()
            assert await reader.scalar(text("SELECT count(*) FROM administration_lock")) == 1
        async with second_engine.begin() as connection:
            assert await connection.scalar(text("SELECT count(*) FROM administration_lock")) == 0
            assert (
                await connection.scalar(
                    text("INSERT INTO administration_lock DEFAULT VALUES RETURNING id")
                )
                == 1
            )
            assert (
                await connection.scalar(
                    text("SELECT datallowconn FROM pg_database WHERE datname=:name"),
                    {"name": worker.template},
                )
                is False
            )
        unexpected_connection = None
        try:
            with pytest.raises(asyncpg.ObjectNotInPrerequisiteStateError):
                unexpected_connection = await asyncpg.connect(
                    worker._url(worker.template).replace("+asyncpg", "")
                )
        finally:
            if unexpected_connection is not None:
                await unexpected_connection.close()
    finally:
        await first_engine.dispose()
        await second_engine.dispose()
        await worker.release(first)
        await worker.release(second)


async def test_late_engine_and_metadata_observers_run_normal_ddl(worker):
    database = await worker.acquire()
    assert database
    engine = create_engine(database.url)
    statements, dropped = [], []

    def observe(_conn, _cursor, statement, *_args):
        statements.append(statement.split()[0])

    def after_drop(*_args, **_kwargs):
        dropped.append(True)

    try:
        event.listen(engine.sync_engine, "before_cursor_execute", observe)
        await database.prepare(engine)
        assert "CREATE" in statements and "DROP" in statements
        event.remove(engine.sync_engine, "before_cursor_execute", observe)
        event.listen(Base.metadata, "after_drop", after_drop)
        try:
            assert database.requires_drop(engine)
            await drop_schema(engine)
            assert dropped == [True]
        finally:
            event.remove(Base.metadata, "after_drop", after_drop)
    finally:
        await engine.dispose()
        await worker.release(database)


async def test_live_connection_prevents_drop_without_forcing_other_connections(worker):
    database = await worker.acquire()
    assert database
    connection = await asyncpg.connect(database.url.replace("+asyncpg", ""))
    try:
        with pytest.raises(asyncpg.ObjectInUseError):
            await worker.release(database)
        assert database.name in worker._created
        assert await connection.fetchval("SELECT 1") == 1
    finally:
        await connection.close()
    await worker.release(database)
    assert database.name not in worker._created


async def test_app_schema_setup_failure_still_disposes_its_clone_engine(worker, monkeypatch):
    database = await worker.acquire()
    assert database
    engine = create_engine(database.url)
    disposed = []

    async def dispose():
        await engine.dispose()
        disposed.append(True)

    async def failed_prepare(_engine):
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        raise RuntimeError("Synthetic app setup failure")

    monkeypatch.setattr(database, "prepare", failed_prepare)
    container = SimpleNamespace(engine=engine, dispose=dispose)
    monkeypatch.setattr(
        conftest,
        "create_app",
        lambda *_args, **_kwargs: SimpleNamespace(state=SimpleNamespace(container=container)),
    )
    fixture = conftest.app.__wrapped__(
        SimpleNamespace(database_url=database.url), None, None, (), database
    )
    with pytest.raises(RuntimeError, match="app setup failure"):
        await anext(fixture)
    assert disposed == [True]
    await worker.release(database)
