"""A cancelled/failed template operation retains ownership for bounded cleanup."""

import asyncio
import os
from collections import Counter
from types import SimpleNamespace

import pytest

import postgres_templates
from postgres_template_store import TemplateWorker


@pytest.fixture
def worker():
    return TemplateWorker("postgresql+asyncpg://localhost/ase_test_" + "a" * 32 + "_master", "x")


async def test_cancellation_finishes_create_bookkeeping_before_it_propagates(worker, monkeypatch):
    started, finish = asyncio.Event(), asyncio.Event()
    calls = []

    class Connection:
        async def execute(self, statement):
            calls.append(statement.split()[0])
            started.set()
            await finish.wait()

        async def close(self):
            calls.append("closed")

    async def connect(*_args, **_kwargs):
        return Connection()

    monkeypatch.setattr("postgres_template_store.asyncpg.connect", connect)
    name = worker._allocate()
    task = asyncio.create_task(worker._command(name))
    await started.wait()
    task.cancel()
    await asyncio.sleep(0)
    assert not task.done()
    finish.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert name in worker._created
    await worker.close()
    assert not worker._created
    assert calls == ["CREATE", "closed", "DROP", "closed"]


async def test_failed_drop_preserves_ownership_and_close_attempts_other_databases(
    worker, monkeypatch
):
    first, second = worker._allocate(), worker._allocate()
    worker._created.update((first, second))
    dropped = []

    async def execute(name, **_kwargs):
        if name == first:
            raise RuntimeError("Synthetic live connection")
        dropped.append(name)
        worker._created.remove(name)

    monkeypatch.setattr(worker, "_execute", execute)
    with pytest.raises(ExceptionGroup, match="cleanup failed"):
        await worker.close()
    assert worker._created == {first}
    assert dropped == [second]


async def test_failed_template_schema_is_disposed_and_still_owned_for_cleanup(worker, monkeypatch):
    disposed = []

    async def dispose():
        disposed.append(True)

    async def create(*_args, **_kwargs):
        raise RuntimeError("Synthetic DDL failure")

    async def command(name, **kwargs):
        if kwargs.get("drop"):
            worker._created.remove(name)
        else:
            worker._created.add(name)

    monkeypatch.setattr("postgres_template_store.schema_fingerprint", lambda: "x")
    monkeypatch.setattr("postgres_template_store.instrumented", lambda _engine: False)
    monkeypatch.setattr(
        "postgres_template_store.create_engine", lambda _url: SimpleNamespace(dispose=dispose)
    )
    monkeypatch.setattr("postgres_template_store.create_schema", create)
    monkeypatch.setattr(worker, "_command", command)
    with pytest.raises(RuntimeError, match="DDL failure"):
        await worker.acquire()
    assert disposed == [True]
    assert len(worker._created) == 1
    await worker.close()
    assert not worker._created


@pytest.mark.parametrize("cleanup_fails", [False, True])
def test_prerequisite_restores_worker_url_on_test_and_cleanup_failure(monkeypatch, cleanup_fails):
    lease = SimpleNamespace(url="postgresql+asyncpg://localhost/owned_clone")
    released = []

    async def acquire():
        return lease

    async def release(database):
        released.append(database)
        if cleanup_fails:
            raise RuntimeError("Synthetic cleanup failure")

    worker = SimpleNamespace(acquire=acquire, release=release)
    request = SimpleNamespace(
        config=SimpleNamespace(
            getoption=lambda _name: True, stash={postgres_templates.COUNTS: Counter()}
        ),
        node=object(),
        getfixturevalue=lambda _name: worker,
    )
    monkeypatch.setattr(postgres_templates, "ordinary_app", lambda _item: True)
    monkeypatch.setenv("ASE_TEST_DATABASE_URL", "postgresql+asyncpg://localhost/owned_worker")
    prerequisite = postgres_templates.template_database.__wrapped__(request)
    assert next(prerequisite) is lease
    assert os.environ["ASE_TEST_DATABASE_URL"].endswith("/owned_clone")
    expected = "cleanup failure" if cleanup_fails else "test failure"
    with pytest.raises(RuntimeError, match=expected):
        prerequisite.throw(RuntimeError("Synthetic test failure"))
    assert os.environ["ASE_TEST_DATABASE_URL"].endswith("/owned_worker")
    assert released == [lease]


@pytest.mark.parametrize("isolated", [False, True])
def test_template_options_fail_before_service_ddl(monkeypatch, isolated):
    options = {"--template-postgres": True, "--isolated-postgres": isolated}
    config = SimpleNamespace(getoption=options.get, stash={})
    monkeypatch.setenv(
        "ASE_TEST_DATABASE_URL", "postgresql+asyncpg://localhost/service?host=other.example"
    )
    with pytest.raises(pytest.UsageError, match=r"requires|without query"):
        postgres_templates.pytest_configure(config)
