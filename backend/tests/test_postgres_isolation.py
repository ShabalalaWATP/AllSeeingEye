"""Database selection and worker naming fail closed before any SQL is executed."""

import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy.engine import make_url

from postgres_isolation import worker_database_url
from pytest_support import apply_markers, refuse_shared_databases_in_parallel


def test_workers_and_runs_have_distinct_private_database_names():
    source = "postgresql+asyncpg://user:synthetic@localhost/service"
    urls = {
        worker_database_url(source, worker, token * 32)
        for worker in ("gw0", "gw1")
        for token in ("a", "b")
    }
    assert len(urls) == 4
    assert all(make_url(url).database != "service" for url in urls)
    assert all(make_url(url).host == "localhost" for url in urls)


@pytest.mark.parametrize("worker,token", [("gw0; DROP DATABASE ase", "a" * 32), ("gw0", "../")])
def test_untrusted_worker_identity_is_rejected(worker, token):
    with pytest.raises(pytest.UsageError, match="identity"):
        worker_database_url("postgresql+asyncpg://localhost/service", worker, token)


def test_sqlite_cannot_be_used_as_a_postgres_service():
    with pytest.raises(pytest.UsageError, match="PostgreSQL"):
        worker_database_url("sqlite+aiosqlite://", "gw0", "a" * 32)


def test_opt_in_allows_only_the_test_service_not_other_shared_urls(monkeypatch):
    for name in tuple(os.environ):
        if name.startswith("ASE_") and (
            name.endswith("_POSTGRES_URL") or name.endswith("_TEST_URL")
        ):
            monkeypatch.delenv(name)
    monkeypatch.setenv("ASE_TEST_DATABASE_URL", "postgresql+asyncpg://localhost/service")
    config = SimpleNamespace(option=SimpleNamespace(numprocesses=2, isolated_postgres=True))
    refuse_shared_databases_in_parallel(config)
    monkeypatch.setenv("ASE_TOKEN_RACE_TEST_URL", "postgresql+asyncpg://localhost/shared")
    with pytest.raises(pytest.UsageError, match="shared PostgreSQL/race"):
        refuse_shared_databases_in_parallel(config)


def test_remote_postgres_cannot_be_used_as_a_disposable_service():
    with pytest.raises(pytest.UsageError, match="local disposable"):
        worker_database_url("postgresql+asyncpg://database.example/service", "gw0", "a" * 32)


@pytest.mark.parametrize("isolated", [False, True])
def test_parallel_rotation_cannot_reset_a_shared_database(monkeypatch, isolated):
    monkeypatch.setenv("ASE_TEST_DATABASE_URL", "postgresql+asyncpg://localhost/service")
    monkeypatch.setenv("ASE_ROTATION_TEST_URL", "postgresql+asyncpg://localhost/rotation")
    config = SimpleNamespace(option=SimpleNamespace(numprocesses=2, isolated_postgres=isolated))
    with pytest.raises(pytest.UsageError, match=r"shared PostgreSQL/race|ASE_ROTATION_TEST_URL"):
        refuse_shared_databases_in_parallel(config)


def test_fixture_closure_and_direct_engine_construction_are_marked():
    def database_test():
        create_engine()  # noqa: F821

    for fixtures, test, expected in [
        (["client", "app"], lambda: None, True),
        ([], database_test, True),
        (["clock"], lambda: None, False),
    ]:
        markers = []
        item = SimpleNamespace(
            path=Path("test_example.py"), fixturenames=fixtures, obj=test, add_marker=markers.append
        )
        apply_markers([item])
        assert ("db" in {marker.name for marker in markers}) == expected


def test_migration_and_race_markers_remain_serial():
    markers = []
    item = SimpleNamespace(
        path=Path("test_example_migration_postgres.py"),
        fixturenames=["race_container"],
        add_marker=markers.append,
    )
    apply_markers([item])
    assert {marker.name for marker in markers} == {"postgres", "migration", "race"}
