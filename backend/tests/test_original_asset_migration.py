"""Disposable schema acceptance and refusal to discard retained asset records."""

import sqlite3
from contextlib import closing

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from ase.adapters.persistence.base import Base
from test_mfa_migration import prepare


def test_upgrade_preserves_existing_data_and_matches_models(tmp_path):
    config, database, _ = prepare(tmp_path)
    command.upgrade(config, "0026")
    with closing(sqlite3.connect(database)) as connection:
        before = connection.execute("SELECT * FROM users").fetchall()
    command.upgrade(config, "0027")
    engine = sa.create_engine(f"sqlite:///{database}")
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(
                connection,
                opts={
                    "include_object": lambda obj, name, kind, reflected, comparison: (
                        kind != "table" or name == "original_assets"
                    )
                },
            )
            assert compare_metadata(context, Base.metadata) == []
    finally:
        engine.dispose()
    command.downgrade(config, "0026")
    command.upgrade(config, "0027")
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT * FROM users").fetchall() == before


def test_downgrade_refuses_even_scrubbed_tombstone(tmp_path):
    config, database, identity = prepare(tmp_path)
    command.upgrade(config, "0027")
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute(
            "INSERT INTO original_assets VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "a" * 32,
                "b" * 32,
                "c" * 32,
                1,
                "",
                "",
                "",
                "",
                0,
                "",
                "",
                "",
                identity,
                None,
                identity,
                "2026-09-07",
                "2026-09-08",
                "2026-09-07",
                "deleted",
                "2026-09-07",
                None,
                None,
            ),
        )
        before = tuple(connection.iterdump())
    with pytest.raises(RuntimeError, match="Original asset records remain"):
        command.downgrade(config, "0026")
    with closing(sqlite3.connect(database)) as connection:
        assert tuple(connection.iterdump()) == before
