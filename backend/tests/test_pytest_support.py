"""The suite's own guards: parallel runs never share a database and schemas start clean."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import inspect, text

from ase.adapters.persistence.base import Base
from ase.adapters.persistence.session import create_engine
from pytest_support import (
    DurationRecorder,
    create_schema,
    disposable_database,
    refuse_shared_databases_in_parallel,
    shared_database_variables,
    skip_sqlite_fsync,
)


def _config(numprocesses: object) -> Any:
    return SimpleNamespace(option=SimpleNamespace(numprocesses=numprocesses))


def test_shared_database_variables_are_named_without_values() -> None:
    environment = {
        "ASE_TEST_DATABASE_URL": "postgresql+asyncpg://shared/db",
        "ASE_TOKEN_RACE_TEST_URL": "",
        "ASE_SCOPE_MIGRATION_POSTGRES_URL": "postgresql://shared/scope",
        "ASE_DATABASE_URL": "sqlite+aiosqlite:///operator.db",
        "PATH": "ignored",
    }
    assert shared_database_variables(environment) == [
        "ASE_SCOPE_MIGRATION_POSTGRES_URL",
        "ASE_TEST_DATABASE_URL",
    ]


def test_parallel_runs_refuse_a_shared_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASE_TEST_DATABASE_URL", "postgresql+asyncpg://shared/secret-db")
    with pytest.raises(pytest.UsageError) as refused:
        refuse_shared_databases_in_parallel(_config(4))
    assert "ASE_TEST_DATABASE_URL" in str(refused.value)
    assert "secret-db" not in str(refused.value)
    for serial in (None, 0):
        refuse_shared_databases_in_parallel(_config(serial))


def test_only_empty_sqlite_databases_skip_the_initial_drop(tmp_path: Path) -> None:
    existing = tmp_path / "existing.sqlite"
    existing.touch()
    assert disposable_database("sqlite+aiosqlite://")
    assert disposable_database("sqlite+aiosqlite:///:memory:")
    assert disposable_database(f"sqlite+aiosqlite:///{tmp_path / 'new.sqlite'}")
    assert not disposable_database(f"sqlite+aiosqlite:///{existing}")
    assert not disposable_database("postgresql+asyncpg://user:pass@localhost/db")


async def test_file_schema_is_created_once_without_fsync(tmp_path: Path) -> None:
    url = f"sqlite+aiosqlite:///{tmp_path / 'schema.sqlite'}"
    engine = create_engine(url)
    skip_sqlite_fsync(engine)
    try:
        await create_schema(engine, fresh=disposable_database(url))
        await create_schema(engine, fresh=disposable_database(url))
        async with engine.connect() as connection:
            names = await connection.run_sync(lambda sync: inspect(sync).get_table_names())
            synchronous = (await connection.execute(text("PRAGMA synchronous"))).scalar()
        assert set(names) == set(Base.metadata.tables)
        assert synchronous == 0
    finally:
        await engine.dispose()


def test_duration_recording_merges_by_file(tmp_path: Path) -> None:
    target = tmp_path / "durations.json"
    target.write_text(json.dumps({"tests/test_kept.py": 3.0, "tests/test_a.py": 9.0}))
    recorder = DurationRecorder(target)
    for nodeid, seconds in [
        ("tests/test_a.py::test_one", 0.25),
        ("tests/test_a.py::test_two[x]", 0.5),
        ("tests/test_b.py::TestGroup::test_three", 1.0),
    ]:
        recorder.pytest_runtest_logreport(SimpleNamespace(nodeid=nodeid, duration=seconds))  # type: ignore[arg-type]
    recorder.pytest_sessionfinish()
    assert json.loads(target.read_text()) == {
        "tests/test_a.py": 0.75,
        "tests/test_b.py": 1.0,
        "tests/test_kept.py": 3.0,
    }
