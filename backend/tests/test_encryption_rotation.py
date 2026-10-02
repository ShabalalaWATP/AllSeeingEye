"""Rotation preflights all consumers and rolls every write back on failure."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table, event, select, update
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from ase.adapters.persistence.base import Base
from ase.adapters.persistence.encryption_rotation import ENCRYPTED_COLUMNS, rotate_encryption_key
from ase.adapters.security.cipher import CipherUnavailable, FernetCipher
from ase.cli_encryption import _read_key

OLD, NEW = "rotation-old-fixture-" * 3, "rotation-new-fixture-" * 3


@pytest.fixture
async def rotation_engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    # This opt-in URL must name this test's fresh disposable database only.
    engine = create_async_engine(
        os.environ.get("ASE_ROTATION_TEST_URL", f"sqlite+aiosqlite:///{tmp_path}/rotation.db")
    )
    metadata = MetaData()
    for name, columns in ENCRYPTED_COLUMNS.items():
        Table(
            name,
            metadata,
            Column("id", Integer, primary_key=True),
            Column("metadata", String),
            *(Column(column, String, nullable=True) for column in columns),
        )
    async with engine.begin() as connection:
        await connection.run_sync(metadata.create_all)
        for table in metadata.tables.values():
            await connection.execute(
                table.insert(),
                [
                    {
                        "id": 1,
                        "metadata": "unchanged",
                        **{
                            column: FernetCipher(OLD).encrypt(table.name + column)
                            for column in ENCRYPTED_COLUMNS[table.name]
                        },
                    },
                    {
                        "id": 2,
                        "metadata": "null-fields",
                        **dict.fromkeys(ENCRYPTED_COLUMNS[table.name]),
                    },
                ],
            )
    yield engine
    async with engine.begin() as connection:
        await connection.run_sync(metadata.drop_all)
    await engine.dispose()


async def snapshot(engine: AsyncEngine) -> dict[str, list[dict[str, object]]]:
    metadata = MetaData()
    async with engine.connect() as connection:
        await connection.run_sync(lambda sync: metadata.reflect(sync, only=list(ENCRYPTED_COLUMNS)))
        return {
            name: [
                dict(row)
                for row in (
                    await connection.execute(select(table).order_by(*table.primary_key.columns))
                ).mappings()
            ]
            for name, table in metadata.tables.items()
        }


async def test_rotation_preserves_plaintext_nulls_and_all_other_metadata(
    rotation_engine: AsyncEngine,
) -> None:
    before = await snapshot(rotation_engine)
    assert await rotate_encryption_key(rotation_engine, OLD, NEW) == 9
    after = await snapshot(rotation_engine)
    for name, rows in after.items():
        for index, row in enumerate(rows):
            assert row["metadata"] == before[name][index]["metadata"]
            for column in ENCRYPTED_COLUMNS[name]:
                value = row[column]
                if value is None:
                    assert before[name][index][column] is None
                else:
                    assert isinstance(value, str)
                    assert FernetCipher(NEW).decrypt(value) == name + column
                    with pytest.raises(CipherUnavailable):
                        FernetCipher(OLD).decrypt(value)


@pytest.mark.parametrize("failure", ["wrong-key", "malformed", "mid-write"])
async def test_any_failure_leaves_all_rows_unchanged(
    rotation_engine: AsyncEngine, failure: str
) -> None:
    if failure == "malformed":
        metadata = MetaData()
        async with rotation_engine.begin() as connection:
            await connection.run_sync(
                lambda sync: metadata.reflect(sync, only=list(ENCRYPTED_COLUMNS))
            )
            await connection.execute(
                update(metadata.tables["acled_credentials"])
                .where(metadata.tables["acled_credentials"].c.id == 1)
                .values(refresh_token_encrypted="broken")
            )
    before = await snapshot(rotation_engine)
    writes = 0

    def fail_write(*args: object) -> None:
        nonlocal writes
        if str(args[2]).startswith("UPDATE"):
            writes += 1
            if writes == 3:
                raise RuntimeError("injected update failure")

    if failure == "mid-write":
        event.listen(rotation_engine.sync_engine, "before_cursor_execute", fail_write)
    try:
        with pytest.raises((CipherUnavailable, RuntimeError)):
            await rotate_encryption_key(
                rotation_engine, "wrong" * 10 if failure == "wrong-key" else OLD, NEW
            )
    finally:
        if failure == "mid-write":
            event.remove(rotation_engine.sync_engine, "before_cursor_execute", fail_write)
    assert await snapshot(rotation_engine) == before


@pytest.mark.parametrize("old,new", [(OLD, OLD), ("short", NEW), (OLD, "short")])
async def test_invalid_or_identical_keys_never_write(
    rotation_engine: AsyncEngine, old: str, new: str
) -> None:
    before = await snapshot(rotation_engine)
    with pytest.raises(CipherUnavailable):
        await rotate_encryption_key(rotation_engine, old, new)
    assert await snapshot(rotation_engine) == before


def test_key_files_are_bounded_regular_files(tmp_path: Path) -> None:
    target = tmp_path / "key"
    target.write_text(OLD)
    target.chmod(0o600)
    assert _read_key(target) == OLD
    target.write_text("x" * 4097)
    with pytest.raises(ValueError):
        _read_key(target)
    with pytest.raises(ValueError):
        _read_key(tmp_path)


async def test_inventory_covers_every_registered_encrypted_column(container) -> None:
    inventory = {
        (name, column) for name, columns in ENCRYPTED_COLUMNS.items() for column in columns
    }
    actual = {
        (table.name, column.name)
        for table in Base.metadata.tables.values()
        for column in table.columns
        if column.name.endswith("_encrypted") or column.name.startswith("encrypted_")
    }
    assert actual == inventory
