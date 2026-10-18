"""Existing accounts start without acceptance; downgrade cannot discard recorded acceptance."""

import asyncio
from datetime import UTC, datetime

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from ase.adapters.persistence.base import Base
from ase.infrastructure.migrations import alembic_config
from test_scope_migration import _insert

TABLES = {"users", "account_requests"}


def _matches_models(connection: sa.Connection) -> None:
    def include(obj: object, name: str | None, kind: str, reflected: bool, compare: object) -> bool:
        table = name if kind == "table" else getattr(getattr(obj, "table", None), "name", None)
        return table in TABLES

    context = MigrationContext.configure(connection, opts={"include_object": include})
    assert compare_metadata(context, Base.metadata) == []


def test_terms_migration_leaves_existing_rows_unaccepted_and_guards_downgrade(tmp_path):
    database = tmp_path / "terms.sqlite"
    config = alembic_config(f"sqlite+aiosqlite:///{database.as_posix()}")
    command.upgrade(config, "0094")
    engine = sa.create_engine(f"sqlite:///{database.as_posix()}")
    try:
        metadata = sa.MetaData()
        metadata.reflect(engine)
        with engine.begin() as connection:
            user = _insert(
                connection, metadata.tables["users"], role="user", email="old@example.com"
            )
            _insert(connection, metadata.tables["account_requests"], status="pending")
        command.upgrade(config, "0095")
        with engine.begin() as connection:
            _matches_models(connection)
            for table in TABLES:
                row = connection.execute(
                    sa.text(f"SELECT terms_version, terms_accepted_at FROM {table}")  # noqa: S608
                ).one()
                assert tuple(row) == (None, None)
            connection.execute(
                sa.text(
                    "UPDATE users SET terms_version = '2026-10-18', terms_accepted_at = :at "
                    "WHERE id = :id"
                ),
                {"at": datetime(2026, 10, 18, tzinfo=UTC), "id": user},
            )
        with pytest.raises(RuntimeError, match="recorded terms acceptance"):
            command.downgrade(config, "0094")
        with engine.begin() as connection:
            connection.execute(sa.text("UPDATE users SET terms_accepted_at = NULL"))
        command.downgrade(config, "0094")
        with engine.connect() as connection:
            for table in TABLES:
                columns = {column["name"] for column in sa.inspect(connection).get_columns(table)}
                assert not columns & {"terms_version", "terms_accepted_at"}
            assert connection.scalar(sa.text("SELECT COUNT(*) FROM users")) == 1
    finally:
        engine.dispose()
        asyncio.set_event_loop(asyncio.new_event_loop())
