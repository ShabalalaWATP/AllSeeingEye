"""Migration 0080 adds per-account bell preferences and rule mutes, and reverses cleanly."""

import importlib.util
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Column, MetaData, Table, Uuid, create_engine, event, inspect
from sqlalchemy.exc import IntegrityError

from ase.adapters.persistence.base import Base
from ase.adapters.persistence.bell_models import BellPreferenceRow, BellRuleMuteRow

NOW = datetime(2026, 10, 1, 12, tzinfo=UTC)
TABLES = {"bell_preferences", "bell_rule_mutes"}


def _migration(connection):
    path = Path(__file__).parents[1] / "alembic/versions/0080_bell_preferences.py"
    spec = importlib.util.spec_from_file_location("bell_preferences_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.op = Operations(MigrationContext.configure(connection))
    return module


def test_bell_preference_migration_constrains_rows_matches_models_and_downgrades() -> None:
    engine = create_engine("sqlite://")
    event.listen(engine, "connect", lambda conn, _: conn.execute("PRAGMA foreign_keys=ON"))
    with engine.begin() as connection:
        metadata = MetaData()
        for name in ("users", "indicators"):
            Table(name, metadata, Column("id", Uuid(), primary_key=True))
        metadata.create_all(connection)
        user, rule = uuid4(), uuid4()
        connection.execute(metadata.tables["users"].insert().values(id=user))
        connection.execute(metadata.tables["indicators"].insert().values(id=rule))
        migration = _migration(connection)
        assert migration.revision == "0080" and migration.down_revision == "0079"
        migration.upgrade()
        assert set(inspect(connection).get_table_names()) >= TABLES
        preferences = BellPreferenceRow.__table__
        mutes = BellRuleMuteRow.__table__
        connection.execute(
            preferences.insert().values(user_id=user, muted_kinds=["alerts"], updated_at=NOW)
        )
        connection.execute(mutes.insert().values(user_id=user, indicator_id=rule, muted_at=NOW))
        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(mutes.insert().values(user_id=user, indicator_id=rule, muted_at=NOW))
        # Deleting the rule removes every account's mute of it.
        connection.execute(metadata.tables["indicators"].delete())
        assert connection.execute(mutes.select()).all() == []

        context = MigrationContext.configure(
            connection,
            opts={
                "include_object": lambda obj, name, kind, reflected, compare: (
                    (kind != "table" or name in TABLES)
                    and (
                        kind == "table"
                        or getattr(obj, "table", None) is None
                        or obj.table.name in TABLES
                    )
                )
            },
        )
        assert compare_metadata(context, Base.metadata) == []
        migration.downgrade()
        assert not TABLES & set(inspect(connection).get_table_names())
