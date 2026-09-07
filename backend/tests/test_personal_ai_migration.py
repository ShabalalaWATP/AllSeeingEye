"""Disposable SQLite/PostgreSQL personal-binding migration and rollback acceptance."""

import asyncio

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from ase.adapters.persistence.base import Base
from ase.infrastructure.migrations import alembic_config
from test_llm_connections_migration import _assert_preserved, _bind, _database, _seed


def verify_schema(connection):
    context = MigrationContext.configure(
        connection,
        opts={
            "include_object": lambda obj, name, kind, reflected, comparison: (
                kind != "table" or name == "llm_connection_bindings"
            ),
        },
    )
    assert compare_metadata(context, Base.metadata) == []


def insert_personal(connection, original):
    table = sa.Table("llm_connection_bindings", sa.MetaData(), autoload_with=connection)
    base = dict(
        connection.execute(sa.select(table).where(table.c.scope_key == "global")).mappings().one()
    )
    owner = original["snapshot"]["llm_usage"][0]["user_id"]
    base.update(scope_key=f"user:{owner}", user_id=owner)
    connection.execute(table.insert().values(**base))
    with pytest.raises(sa.exc.IntegrityError), connection.begin_nested():
        connection.execute(table.insert().values(**{**base, "scope_key": "user:duplicate"}))
    with pytest.raises(sa.exc.IntegrityError), connection.begin_nested():
        connection.execute(
            table.update()
            .where(table.c.user_id.is_not(None))
            .values(team_id=original["snapshot"]["reports"][0]["team_id"])
        )


@pytest.mark.parametrize("dialect", ["sqlite", "postgresql"])
async def test_personal_migration_preserves_existing_bindings_and_guards_downgrade(
    dialect, tmp_path
):
    async with _database(dialect, tmp_path) as url:
        config = alembic_config(url)
        await asyncio.to_thread(command.upgrade, config, "0027")
        engine = create_async_engine(url, poolclass=NullPool)
        try:
            async with engine.begin() as connection:
                original = await connection.run_sync(_seed)
                await connection.run_sync(lambda sync: _bind(sync, original))
                before = [
                    dict(row)
                    for row in (
                        await connection.execute(
                            sa.text("SELECT * FROM llm_connection_bindings ORDER BY scope_key")
                        )
                    ).mappings()
                ]
            await asyncio.to_thread(command.upgrade, config, "0028")
            async with engine.begin() as connection:
                await connection.run_sync(verify_schema)
                await connection.run_sync(lambda sync: _assert_preserved(sync, original))
                after = [
                    dict(row)
                    for row in (
                        await connection.execute(
                            sa.text("SELECT * FROM llm_connection_bindings ORDER BY scope_key")
                        )
                    ).mappings()
                ]
                assert [
                    {key: row[key] for key in before[index]} for index, row in enumerate(after)
                ] == before
                assert all(row["user_id"] is None for row in after)
                await connection.run_sync(lambda sync: insert_personal(sync, original))
            with pytest.raises(RuntimeError, match="personal AI overrides"):
                await asyncio.to_thread(command.downgrade, config, "0027")
            async with engine.begin() as connection:
                assert (
                    await connection.scalar(sa.text("SELECT version_num FROM alembic_version"))
                    == "0028"
                )
                await connection.execute(
                    sa.text("DELETE FROM llm_connection_bindings WHERE user_id IS NOT NULL")
                )
            await asyncio.to_thread(command.downgrade, config, "0027")
            async with engine.connect() as connection:
                restored = [
                    dict(row)
                    for row in (
                        await connection.execute(
                            sa.text("SELECT * FROM llm_connection_bindings ORDER BY scope_key")
                        )
                    ).mappings()
                ]
                assert restored == before
                await connection.run_sync(lambda sync: _assert_preserved(sync, original))
            await asyncio.to_thread(command.upgrade, config, "0028")
            async with engine.connect() as connection:
                await connection.run_sync(verify_schema)
        finally:
            await engine.dispose()
