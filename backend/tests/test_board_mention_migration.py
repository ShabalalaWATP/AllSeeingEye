"""Migration 0081 adds bounded board mention rows that follow their post, and reverses."""

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
from ase.adapters.persistence.team_board_models import TeamBoardMentionRow

NOW = datetime(2026, 10, 1, 12, tzinfo=UTC)
TABLE = "team_board_mentions"


def _migration(connection):
    path = Path(__file__).parents[1] / "alembic/versions/0081_board_mentions.py"
    spec = importlib.util.spec_from_file_location("board_mentions_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.op = Operations(MigrationContext.configure(connection))
    return module


def test_board_mention_migration_constrains_rows_matches_models_and_downgrades() -> None:
    engine = create_engine("sqlite://")
    event.listen(engine, "connect", lambda conn, _: conn.execute("PRAGMA foreign_keys=ON"))
    with engine.begin() as connection:
        metadata = MetaData()
        for name in ("users", "teams", "team_board_posts"):
            Table(name, metadata, Column("id", Uuid(), primary_key=True))
        metadata.create_all(connection)
        user, other, team, post = uuid4(), uuid4(), uuid4(), uuid4()
        connection.execute(metadata.tables["users"].insert(), [{"id": user}, {"id": other}])
        connection.execute(metadata.tables["teams"].insert().values(id=team))
        connection.execute(metadata.tables["team_board_posts"].insert().values(id=post))
        migration = _migration(connection)
        assert migration.revision == "0081" and migration.down_revision == "0080"
        migration.upgrade()
        rows = TeamBoardMentionRow.__table__

        def mention(recipient: object, handle: str) -> dict[str, object]:
            return {
                "post_id": post,
                "recipient_id": recipient,
                "team_id": team,
                "handle": handle,
                "created_at": NOW,
            }

        connection.execute(rows.insert().values(**mention(user, "analyst")))
        for duplicate in (mention(user, "other_name"), mention(other, "analyst")):
            with pytest.raises(IntegrityError), connection.begin_nested():
                connection.execute(rows.insert().values(**duplicate))
        # Removing the post removes its mentions.
        connection.execute(metadata.tables["team_board_posts"].delete())
        assert connection.execute(rows.select()).all() == []

        context = MigrationContext.configure(
            connection,
            opts={
                "include_object": lambda obj, name, kind, reflected, compare: (
                    (kind != "table" or name == TABLE)
                    and (
                        kind == "table"
                        or getattr(obj, "table", None) is None
                        or obj.table.name == TABLE
                    )
                )
            },
        )
        assert compare_metadata(context, Base.metadata) == []
        migration.downgrade()
        assert TABLE not in inspect(connection).get_table_names()
