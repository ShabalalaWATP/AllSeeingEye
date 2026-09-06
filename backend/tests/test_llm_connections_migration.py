"""Synthetic migration parity preserves provider configuration and frozen reports."""

import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from sqlalchemy.ext.asyncio import create_async_engine

from ase.infrastructure.migrations import alembic_config
from test_scope_migration import _insert

LEGACY_TABLES = ("llm_profiles", "llm_usage", "reports", "report_versions")


@asynccontextmanager
async def _database(dialect: str, tmp_path: Path) -> AsyncIterator[str]:
    if dialect == "sqlite":
        yield f"sqlite+aiosqlite:///{tmp_path / 'connections.db'}"
        return
    source = os.environ.get("ASE_LLM_MIGRATION_POSTGRES_URL")
    if not source:
        pytest.skip("Set ASE_LLM_MIGRATION_POSTGRES_URL to an owned disposable PostgreSQL server")
    url = sa.make_url(source)
    assert url.drivername == "postgresql+asyncpg"
    name = f"ase_llm_migration_{uuid4().hex}"
    engine = create_async_engine(url, isolation_level="AUTOCOMMIT")
    try:
        async with engine.connect() as connection:
            await connection.execute(sa.text(f'CREATE DATABASE "{name}"'))
        try:
            yield url.set(database=name).render_as_string(hide_password=False)
        finally:
            async with engine.connect() as connection:
                await connection.execute(sa.text(f'DROP DATABASE "{name}"'))
    finally:
        await engine.dispose()


def _snapshot(connection: sa.Connection) -> dict[str, list[dict[str, Any]]]:
    metadata = sa.MetaData()
    metadata.reflect(connection)
    return {
        name: [dict(row) for row in connection.execute(sa.select(metadata.tables[name])).mappings()]
        for name in LEGACY_TABLES
    }


def _seed(connection: sa.Connection) -> dict[str, Any]:
    metadata = sa.MetaData()
    metadata.reflect(connection)
    tables = metadata.tables
    owner = _insert(connection, tables["users"], email="migration@example.com", role="admin")
    team = _insert(connection, tables["teams"], name="Synthetic team", created_by=owner)
    profiles = [
        _insert(
            connection,
            tables["llm_profiles"],
            name=f"Legacy profile {index}",
            base_url="http://127.0.0.1:11434/v1",
            model=f"legacy-model-{index}",
            api_key_encrypted=f"synthetic-opaque-ciphertext-{index}",
            api_key_hint="test",
            roles=["assessment", "devil", "translation"] if index == 0 else ["embeddings"],
            enabled=index == 0,
            max_output_tokens=4096,
            temperature=0.25,
        )
        for index in range(2)
    ]
    report = _insert(connection, tables["reports"], created_by=owner, team_id=team)
    _insert(
        connection,
        tables["report_versions"],
        report_id=report,
        profile_id=profiles[0],
        model="legacy-model-0",
        evidence=[{"id": "frozen-source", "hash": "unchanged"}],
        body={"summary": "Historical research must remain unchanged"},
        analysis={"legacy": {"profile": profiles[0]}},
    )
    _insert(
        connection,
        tables["llm_usage"],
        id=1,
        profile_id=profiles[0],
        user_id=owner,
        purpose="draft",
        prompt_tokens=120,
        completion_tokens=35,
    )
    return {"owner": owner, "team": team, "profiles": profiles, "snapshot": _snapshot(connection)}


def _assert_preserved(connection: sa.Connection, original: dict[str, Any]) -> None:
    current = _snapshot(connection)
    for name, previous_rows in original["snapshot"].items():
        assert len(current[name]) == len(previous_rows)
        by_id = {row["id"]: row for row in current[name]}
        for previous in previous_rows:
            assert {key: by_id[previous["id"]][key] for key in previous} == previous


def _assert_legacy_defaults(connection: sa.Connection) -> None:
    metadata = sa.MetaData()
    metadata.reflect(connection)
    profiles = metadata.tables["llm_profiles"]
    for row in connection.execute(sa.select(profiles)).mappings():
        assert row["revision"] == 1
        assert row["test_generation"] == 0
        assert all(
            row[key] is None
            for key in ("reasoning_effort", "tested_at", "tested_revision", "tested_config_hash")
        )
    bindings = metadata.tables["llm_connection_bindings"]
    assert connection.scalar(sa.select(sa.func.count()).select_from(bindings)) == 0
    foreign_keys = {
        tuple(key["constrained_columns"]): key
        for key in sa.inspect(connection).get_foreign_keys(bindings.name)
    }
    assert foreign_keys[("profile_id",)]["referred_table"] == "llm_profiles"
    assert foreign_keys[("profile_id",)]["options"]["ondelete"] == "RESTRICT"
    assert foreign_keys[("team_id",)]["referred_table"] == "teams"
    assert foreign_keys[("team_id",)]["options"]["ondelete"] == "CASCADE"
    sequence = metadata.tables["llm_binding_sequence"]
    assert [dict(row) for row in connection.execute(sa.select(sequence)).mappings()] == [
        {"id": 1, "value": 0}
    ]
    for identifier in (1, 2):
        with pytest.raises(sa.exc.IntegrityError), connection.begin_nested():
            connection.execute(sequence.insert().values(id=identifier, value=0))


def _assert_reverted(connection: sa.Connection) -> None:
    inspector = sa.inspect(connection)
    assert "llm_binding_sequence" not in inspector.get_table_names()
    assert "llm_connection_bindings" not in inspector.get_table_names()
    columns = {column["name"] for column in inspector.get_columns("llm_profiles")}
    assert not columns.intersection(
        {
            "test_generation",
            "reasoning_effort",
            "revision",
            "tested_at",
            "tested_revision",
            "tested_config_hash",
        }
    )


def _bind(connection: sa.Connection, original: dict[str, Any]) -> None:
    bindings = sa.Table("llm_connection_bindings", sa.MetaData(), autoload_with=connection)
    profile = original["snapshot"]["llm_profiles"][0]["id"]
    values = {
        "scope_key": "global",
        "team_id": None,
        "profile_id": profile,
        "profile_revision": 1,
        "tested_config_hash": "f" * 64,
        "activated_at": datetime(2026, 9, 6, tzinfo=UTC),
        "activated_by": original["snapshot"]["llm_usage"][0]["user_id"],
        "revision": 1,
    }
    connection.execute(bindings.insert().values(**values))
    with pytest.raises(sa.exc.IntegrityError), connection.begin_nested():
        connection.execute(bindings.insert().values(**values))
    # NULL team uniqueness alone permits extra global rows under different keys.
    with pytest.raises(sa.exc.IntegrityError), connection.begin_nested():
        connection.execute(bindings.insert().values(**{**values, "scope_key": "extra-global"}))
    team = original["snapshot"]["reports"][0]["team_id"]
    values.update(scope_key=f"team:{team}", team_id=team)
    connection.execute(bindings.insert().values(**values))
    with pytest.raises(sa.exc.IntegrityError), connection.begin_nested():
        connection.execute(bindings.insert().values(**{**values, "scope_key": "team:duplicate"}))
    assert connection.scalar(sa.select(sa.func.count()).select_from(bindings)) == 2


@pytest.mark.parametrize("dialect", ["sqlite", "postgresql"])
async def test_connections_migration_preserves_legacy_configuration_and_reports(
    dialect: str, tmp_path: Path
) -> None:
    async with _database(dialect, tmp_path) as url:
        config = alembic_config(url)
        await asyncio.to_thread(command.upgrade, config, "0016")
        engine = create_async_engine(url)
        try:
            async with engine.begin() as connection:
                original = await connection.run_sync(_seed)
            await asyncio.to_thread(command.upgrade, config, "0017")
            async with engine.connect() as connection:
                await connection.run_sync(lambda sync: _assert_preserved(sync, original))
                await connection.run_sync(_assert_legacy_defaults)
            await asyncio.to_thread(command.downgrade, config, "0016")
            async with engine.connect() as connection:
                await connection.run_sync(lambda sync: _assert_preserved(sync, original))
                await connection.run_sync(_assert_reverted)
        finally:
            await engine.dispose()


@pytest.mark.parametrize("dialect", ["sqlite", "postgresql"])
@pytest.mark.parametrize("configuration", ["bindings", "reasoning"])
async def test_connections_migration_refuses_lossy_downgrade(
    dialect: str, configuration: str, tmp_path: Path
) -> None:
    async with _database(dialect, tmp_path) as url:
        config = alembic_config(url)
        await asyncio.to_thread(command.upgrade, config, "0016")
        engine = create_async_engine(url)
        try:
            async with engine.begin() as connection:
                original = await connection.run_sync(_seed)
            await asyncio.to_thread(command.upgrade, config, "0017")
            async with engine.begin() as connection:
                await connection.execute(sa.text("UPDATE llm_binding_sequence SET value = 7"))
                await connection.execute(sa.text("UPDATE llm_profiles SET test_generation = 3"))
                if configuration == "bindings":
                    await connection.run_sync(lambda sync: _bind(sync, original))
                else:
                    await connection.execute(
                        sa.text("UPDATE llm_profiles SET reasoning_effort = 'max'")
                    )
            with pytest.raises(RuntimeError, match=r"(?i)(binding|reasoning)"):
                await asyncio.to_thread(command.downgrade, config, "0016")
            async with engine.begin() as connection:
                assert await connection.scalar(
                    sa.text("SELECT version_num FROM alembic_version")
                ) == ("0017")
                await connection.run_sync(lambda sync: _assert_preserved(sync, original))
                assert (
                    await connection.scalar(sa.text("SELECT value FROM llm_binding_sequence")) == 7
                )
                assert list(
                    await connection.scalars(sa.text("SELECT test_generation FROM llm_profiles"))
                ) == [3, 3]
                if configuration == "bindings":
                    assert (
                        await connection.scalar(
                            sa.text("SELECT COUNT(*) FROM llm_connection_bindings")
                        )
                        == 2
                    )
                    await connection.execute(sa.text("DELETE FROM llm_connection_bindings"))
                else:
                    assert (
                        await connection.scalar(
                            sa.text(
                                "SELECT COUNT(*) FROM llm_profiles WHERE reasoning_effort = 'max'"
                            )
                        )
                        == 2
                    )
                    await connection.execute(
                        sa.text("UPDATE llm_profiles SET reasoning_effort = NULL")
                    )
            # Only synthetic new configuration is removed; legacy data still survives reversal.
            await asyncio.to_thread(command.downgrade, config, "0016")
            async with engine.connect() as connection:
                await connection.run_sync(lambda sync: _assert_preserved(sync, original))
                await connection.run_sync(_assert_reverted)
        finally:
            await engine.dispose()
