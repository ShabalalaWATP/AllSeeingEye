"""PostgreSQL pools recover stale connections and fail fast; SQLite pools are unchanged."""

from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy.pool import AsyncAdaptedQueuePool, StaticPool

from ase.adapters.persistence.session import create_engine, engine_options
from ase.infrastructure.settings import Settings

# No credentials and a reserved host: creating an engine never connects.
POSTGRES_URL = "postgresql+asyncpg://ase@db.invalid:5432/ase"


def test_operator_pool_settings_are_validated_and_sqlite_ignores_them():
    settings = Settings(
        env="test", database_pool_size=4, database_max_overflow=0, database_pool_timeout=2
    )
    options = engine_options(
        POSTGRES_URL,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_timeout=settings.database_pool_timeout,
    )
    assert (options["pool_size"], options["max_overflow"], options["pool_timeout"]) == (4, 0, 2)
    assert engine_options("sqlite+aiosqlite://", pool_size=4) == engine_options(
        "sqlite+aiosqlite://"
    )
    for changes in (
        {"database_pool_size": 0},
        {"database_max_overflow": -1},
        {"database_pool_timeout": 0},
    ):
        with pytest.raises(ValidationError):
            Settings(env="test", **changes)


def test_postgres_options_pre_ping_recycle_and_bound_waits() -> None:
    assert engine_options(POSTGRES_URL) == {
        "pool_pre_ping": True,
        "pool_recycle": 1800,
        "pool_size": 10,
        "max_overflow": 10,
        "pool_timeout": 10,
    }


async def test_postgres_engine_applies_the_pool_options() -> None:
    engine = create_engine(POSTGRES_URL)
    try:
        pool = engine.pool
        assert isinstance(pool, AsyncAdaptedQueuePool)
        assert pool.size() == 10 and pool.timeout() == 10
        assert pool._max_overflow == 10 and pool._recycle == 1800 and pool._pre_ping
    finally:
        await engine.dispose()


def test_sqlite_options_are_unchanged(tmp_path: Path) -> None:
    same_thread = {"connect_args": {"check_same_thread": False}}
    in_memory = {**same_thread, "poolclass": StaticPool}
    assert engine_options("sqlite+aiosqlite://") == in_memory
    assert engine_options("sqlite+aiosqlite:///:memory:") == in_memory
    file_url = f"sqlite+aiosqlite:///{(tmp_path / 'ase.db').as_posix()}"
    assert engine_options(file_url) == same_thread


async def test_sqlite_engines_keep_their_pools(tmp_path: Path) -> None:
    memory = create_engine("sqlite+aiosqlite://")
    file_backed = create_engine(f"sqlite+aiosqlite:///{(tmp_path / 'ase.db').as_posix()}")
    try:
        assert isinstance(memory.pool, StaticPool)
        assert not file_backed.pool._pre_ping and file_backed.pool._recycle == -1
    finally:
        await memory.dispose()
        await file_backed.dispose()
