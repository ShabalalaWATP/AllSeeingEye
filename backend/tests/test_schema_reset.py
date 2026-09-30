"""Schema resets retain real DDL semantics for empty, partial and populated databases."""

from types import SimpleNamespace

import pytest
from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    event,
    func,
    inspect,
    select,
)
from sqlalchemy.exc import IntegrityError

import pytest_support
from ase.adapters.persistence.session import create_engine


@pytest.mark.parametrize("initial", ["fresh", "empty", "partial", "full"])
async def test_resets_preserve_defaults_constraints_hooks_and_unmanaged_tables(
    tmp_path, monkeypatch, initial
):
    metadata = MetaData()
    parent = Table(
        "reset_parent",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("state", String, nullable=False, server_default="ready"),
    )
    child = Table(
        "reset_child",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("parent_id", ForeignKey(parent.c.id), nullable=False),
        Column("score", Integer, nullable=False, server_default="7"),
        CheckConstraint("score >= 0", name="ck_reset_score"),
    )
    Index("ix_reset_parent", child.c.parent_id)
    unmanaged = Table("unmanaged_fixture", MetaData(), Column("id", Integer, primary_key=True))
    monkeypatch.setattr(pytest_support, "Base", SimpleNamespace(metadata=metadata))
    engine = create_engine(f"sqlite+aiosqlite:///{tmp_path / 'reset.sqlite'}")

    @event.listens_for(engine.sync_engine, "connect")
    def enable_foreign_keys(connection, _record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    observed = []
    try:
        if initial != "fresh":
            async with engine.begin() as connection:
                await connection.run_sync(unmanaged.create)
                await connection.execute(unmanaged.insert().values(id=99))
                if initial in {"partial", "full"}:
                    tables = [parent] if initial == "partial" else [parent, child]
                    await connection.run_sync(metadata.create_all, tables=tables)
                    await connection.execute(parent.insert().values(id=1))
                    if initial == "full":
                        await connection.execute(child.insert().values(id=1, parent_id=1))

        @event.listens_for(metadata, "after_create")
        def created(_metadata, connection, **_kwargs):
            observed.append(connection.dialect.name)

        for reset in range(2):
            await pytest_support.create_schema(engine, fresh=initial == "fresh" and reset == 0)
            async with engine.begin() as connection:
                names = await connection.run_sync(lambda sync: inspect(sync).get_table_names())
                assert {parent.name, child.name} <= set(names)
                assert await connection.scalar(select(func.count()).select_from(parent)) == 0
                assert await connection.scalar(select(func.count()).select_from(child)) == 0
                if initial != "fresh":
                    assert await connection.scalar(select(unmanaged.c.id)) == 99
                indexes = await connection.run_sync(
                    lambda sync: inspect(sync).get_indexes(child.name)
                )
                assert {index["name"] for index in indexes} == {"ix_reset_parent"}
                await connection.execute(parent.insert().values(id=1))
                await connection.execute(child.insert().values(id=1, parent_id=1))
                assert await connection.scalar(select(parent.c.state)) == "ready"
                assert await connection.scalar(select(child.c.score)) == 7
                with pytest.raises(IntegrityError):
                    async with connection.begin_nested():
                        await connection.execute(child.insert().values(id=2, parent_id=999))
                with pytest.raises(IntegrityError):
                    async with connection.begin_nested():
                        await connection.execute(child.insert().values(id=2, parent_id=1, score=-1))
        assert observed == ["sqlite", "sqlite"]
    finally:
        await engine.dispose()
