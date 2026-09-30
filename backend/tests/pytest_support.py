"""Suite-wide pytest rules used by conftest.py: markers, parallel-run guards and durations.

Markers follow file names so new files are classified without extra boilerplate:
``*_postgres.py`` needs a disposable PostgreSQL server, ``*migration*.py`` runs Alembic
revisions, and ``*_races.py``, ``*_concurrency*.py`` or the ``race_container`` fixture use
real multi-connection databases. Tests elsewhere carry the same markers explicitly.
"""

from __future__ import annotations

import json
import math
import os
from collections import defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine

from ase.adapters.persistence.base import Base
from database_markers import file_constructs_database, uses_database

SHARED_DATABASE_VARIABLES = frozenset(
    {"ASE_TEST_DATABASE_URL", "ASE_TOKEN_RACE_TEST_URL", "ASE_ROTATION_TEST_URL"}
)


def shared_database_variables(environment: Mapping[str, str]) -> list[str]:
    """Configured databases that every test process would share, by variable name."""
    return sorted(
        name
        for name, value in environment.items()
        if value
        and (
            name in SHARED_DATABASE_VARIABLES
            or (name.startswith("ASE_") and name.endswith("_POSTGRES_URL"))
        )
    )


def refuse_shared_databases_in_parallel(config: pytest.Config) -> None:
    """Parallel workers would drop and recreate one shared schema under each other."""
    isolated = getattr(config.option, "isolated_postgres", False)
    names = shared_database_variables(os.environ)
    if isolated and names != ["ASE_TEST_DATABASE_URL"]:
        raise pytest.UsageError(
            "--isolated-postgres requires only ASE_TEST_DATABASE_URL; "
            "unset other shared PostgreSQL/race URLs."
        )
    if not getattr(config.option, "numprocesses", None):
        return
    if (
        isolated
        and names == ["ASE_TEST_DATABASE_URL"]
        and make_url(os.environ["ASE_TEST_DATABASE_URL"]).get_backend_name() == "postgresql"
    ):
        return
    if names:
        raise pytest.UsageError(
            "Parallel tests need private databases: unset "
            f"{', '.join(names)}, run serially, or opt into --isolated-postgres with only "
            "ASE_TEST_DATABASE_URL set."
        )


def disposable_database(url: str) -> bool:
    """In-memory SQLite, or a SQLite file not yet created (such as one under tmp_path)."""
    parsed = make_url(url)
    if parsed.get_backend_name() != "sqlite":
        return False
    return parsed.database in (None, "", ":memory:") or not Path(parsed.database).exists()


def skip_sqlite_fsync(engine: AsyncEngine) -> None:
    """Test files need no crash durability; locking and visibility are unchanged."""
    if engine.dialect.name != "sqlite":
        return

    def no_sync(dbapi_connection: Any, _record: object) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA synchronous=OFF")
        cursor.close()

    event.listen(engine.sync_engine, "connect", no_sync)


async def create_schema(engine: AsyncEngine, *, fresh: bool) -> None:
    """Create every table; an existing shared database is dropped and recreated first."""
    async with engine.begin() as connection:
        if not fresh:
            await connection.run_sync(Base.metadata.drop_all)
        if connection.dialect.name == "sqlite":
            # pysqlite autocommits each DDL statement unless a transaction is open, which
            # costs a journal file and a sync per table on file-backed databases.
            await connection.exec_driver_sql("BEGIN")
        await connection.run_sync(Base.metadata.create_all, checkfirst=not fresh)


async def drop_schema(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)


def uses_report_job_worker(item: pytest.Item) -> bool:
    """Identify report-worker helpers, including imports renamed by a test module."""
    namespace = getattr(getattr(item, "obj", None), "__globals__", {})
    return any(
        getattr(value, "__module__", None) == "report_job_api_helpers"
        and getattr(value, "__name__", None) == "work"
        for value in namespace.values()
    )


def apply_markers(items: Iterable[pytest.Item]) -> None:
    for item in items:
        name = item.path.stem
        if name.endswith("_postgres"):
            item.add_marker(pytest.mark.postgres)
        if "migration" in name:
            item.add_marker(pytest.mark.migration)
        fixtures = getattr(item, "fixturenames", ())
        if {"app", "container", "client", "engine", "db_engine"}.intersection(fixtures):
            item.add_marker(pytest.mark.db)
        # Pytest expands transitive fixtures. Inspect their factories too, covering
        # independently named persistence fixtures without a growing name allowlist.
        factories = getattr(getattr(item, "_fixtureinfo", None), "name2fixturedefs", {})
        functions = [
            definition.func for definitions in factories.values() for definition in definitions
        ]
        functions.append(getattr(item, "obj", None))
        if file_constructs_database(item.path) or any(
            uses_database(function) for function in functions
        ):
            item.add_marker(pytest.mark.db)
        if "_races" in name or "_concurrency" in name or "race_container" in fixtures:
            item.add_marker(pytest.mark.race)
        # Imported helper identity avoids a growing list of file-specific deadlines.
        if uses_report_job_worker(item):
            item.add_marker(pytest.mark.slow)
            item.add_marker(pytest.mark.timeout(660))


class DurationRecorder:
    """Sums setup, call and teardown time per test file for balanced CI shards.

    Files run this session replace their earlier entries; other entries are kept, so the
    suite can be recorded in several partial runs.
    """

    def __init__(self, target: Path) -> None:
        self.target = target
        self.seconds: defaultdict[str, float] = defaultdict(float)

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        self.seconds[report.nodeid.split("::", 1)[0]] += report.duration

    def pytest_sessionfinish(self) -> None:
        recorded: dict[str, float] = {}
        if self.target.exists():
            recorded = json.loads(self.target.read_text(encoding="utf-8"))
        recorded.update(
            (name, round(seconds, 2))
            for name, seconds in self.seconds.items()
            if math.isfinite(seconds)
        )
        ordered = dict(sorted(recorded.items()))
        text = json.dumps(ordered, indent=1) + "\n"
        self.target.write_text(text, encoding="utf-8", newline="\n")
