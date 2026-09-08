"""Disposable PostgreSQL settings and independent FIRMS transaction barriers."""

import asyncio
import os
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from ase.adapters.persistence.users import SqlUserRepository


@pytest.fixture
async def settings(settings):
    source = os.environ.get("ASE_FIRMS_CONCURRENCY_POSTGRES_URL")
    if not source:
        pytest.skip("Set ASE_FIRMS_CONCURRENCY_POSTGRES_URL to a disposable PostgreSQL server")
    url = make_url(source)
    assert url.drivername == "postgresql+asyncpg"
    assert url.host in {"127.0.0.1", "localhost", "::1"}
    name = f"ase_firms_race_{uuid4().hex}"
    database = create_async_engine(url, isolation_level="AUTOCOMMIT")
    try:
        async with database.connect() as connection:
            await connection.execute(text(f'CREATE DATABASE "{name}"'))
        try:
            yield settings.model_copy(
                update={
                    "database_url": url.set(database=name).render_as_string(hide_password=False),
                }
            )
        finally:
            async with database.connect() as connection:
                await connection.execute(text(f'DROP DATABASE "{name}"'))
    finally:
        await database.dispose()


async def invoke(container, actor, method, *args, pids=None, label=None):
    # Keep each connection checked out across the network pause and internal commits.
    async with container.engine.connect() as connection, AsyncSession(bind=connection) as session:
        if pids is not None:
            pids[label] = await session.scalar(text("SELECT pg_backend_pid()"))
        return await getattr(container.admin_firms_credentials(session), method)(actor, *args)


async def observe_lock(container, pid):
    async with asyncio.timeout(10), container.session_factory() as session:
        while True:
            state = await session.scalar(
                text("SELECT wait_event_type FROM pg_stat_activity WHERE pid = :pid"),
                {"pid": pid},
            )
            if state == "Lock":
                return
            await session.rollback()
            await asyncio.sleep(0.01)


def watch_lock(monkeypatch, task_name, pids, waiting):
    original = SqlUserRepository.lock_administration

    async def lock(repository):
        task = asyncio.current_task()
        if task and task.get_name() == task_name:
            pids[task_name] = await repository._session.scalar(text("SELECT pg_backend_pid()"))
            waiting.set()
        await original(repository)

    monkeypatch.setattr(SqlUserRepository, "lock_administration", lock)


async def settle(release, *tasks):
    release.set()
    for task in tasks:
        if task is not None and not task.done():
            task.cancel()
    await asyncio.gather(*(task for task in tasks if task is not None), return_exceptions=True)
