"""Migration 0055 adds field visibility and avatars without widening privacy on downgrade."""

from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect

VERSIONS = Path(__file__).parents[1] / "alembic/versions"


def _load(name: str) -> ModuleType:
    path = next(VERSIONS.glob(f"{name}_*.py"))
    spec = importlib.util.spec_from_file_location(f"migration_{name}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_directory_avatar_migration_round_trip_and_guards() -> None:
    profiles_migration = _load("0046")
    module = _load("0055")
    assert module.revision == "0055" and module.down_revision == "0054"
    engine = create_engine("sqlite://")
    try:
        with engine.begin() as connection:
            operations = Operations(MigrationContext.configure(connection))
            connection.execute(sa.text("CREATE TABLE users (id CHAR(32) PRIMARY KEY)"))
            profiles_migration.op = operations
            profiles_migration.upgrade()
            user_id = uuid4().hex
            connection.execute(sa.text("INSERT INTO users (id) VALUES (:id)"), {"id": user_id})
            connection.execute(
                sa.text(
                    "INSERT INTO directory_profiles (user_id, username, organisation) "
                    "VALUES (:id, 'legacy', 'Desk')"
                ),
                {"id": user_id},
            )

            module.op = operations
            module.upgrade()
            columns = {
                column["name"] for column in inspect(connection).get_columns("directory_profiles")
            }
            assert {"show_organisation", "show_timezone", "avatar_sha256"} <= columns
            assert "directory_avatars" in inspect(connection).get_table_names()
            row = connection.execute(
                sa.text("SELECT show_organisation, show_timezone FROM directory_profiles")
            ).one()
            # Existing profiles keep their previous visibility: fields shown, timezone private.
            assert tuple(row) == (1, 0)

            connection.execute(
                sa.text(
                    "INSERT INTO directory_avatars (user_id, content_type, sha256, byte_count, "
                    "width, height, content, updated_at) VALUES (:id, 'image/webp', :sha, 3, "
                    "256, 256, :content, :at)"
                ),
                {
                    "id": user_id,
                    "sha": "0" * 64,
                    "content": b"abc",
                    "at": datetime.now(UTC).isoformat(),
                },
            )
            with pytest.raises(sa.exc.IntegrityError), connection.begin_nested():
                connection.execute(
                    sa.text(
                        "INSERT INTO directory_avatars (user_id, content_type, sha256, "
                        "byte_count, width, height, content, updated_at) VALUES "
                        "(:id, 'image/svg+xml', :sha, 3, 256, 256, :content, :at)"
                    ),
                    {
                        "id": uuid4().hex,
                        "sha": "0" * 64,
                        "content": b"abc",
                        "at": datetime.now(UTC).isoformat(),
                    },
                )
            with pytest.raises(RuntimeError, match="avatars remain"):
                module.downgrade()
            connection.execute(sa.text("DELETE FROM directory_avatars"))
            connection.execute(sa.text("UPDATE directory_profiles SET show_organisation = 0"))
            with pytest.raises(RuntimeError, match="hidden directory fields"):
                module.downgrade()
            connection.execute(sa.text("UPDATE directory_profiles SET show_organisation = 1"))
            module.downgrade()
            columns = {
                column["name"] for column in inspect(connection).get_columns("directory_profiles")
            }
            assert "show_organisation" not in columns and "avatar_sha256" not in columns
            assert "show_timezone" in columns
            assert "directory_avatars" not in inspect(connection).get_table_names()
    finally:
        engine.dispose()
