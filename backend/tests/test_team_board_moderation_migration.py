"""Migration 0052 classifies existing tombstones and adds board read cursors."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError


def _load(name: str) -> ModuleType:
    path = Path(__file__).parents[1] / "alembic/versions" / name
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _insert(connection, text_value: str, deleted: bool) -> str:  # type: ignore[no-untyped-def]
    post_id = uuid4().hex
    connection.execute(
        text(
            "INSERT INTO team_board_posts (id, team_id, author_id, text, created_at, updated_at,"
            " is_pinned, deleted_at, revision) VALUES (:id, :team, :author, :text,"
            " '2026-09-15', '2026-09-15', 0, :deleted, 1)"
        ),
        {
            "id": post_id,
            "team": uuid4().hex,
            "author": uuid4().hex,
            "text": text_value,
            "deleted": "2026-09-15" if deleted else None,
        },
    )
    return post_id


def test_board_moderation_migration_upgrade_and_downgrade() -> None:
    board, moderation = (
        _load("0048_team_board.py"),
        _load("0052_team_board_moderation_and_reads.py"),
    )
    assert moderation.revision == "0052" and moderation.down_revision == "0051"
    engine = create_engine("sqlite://")
    try:
        with engine.begin() as connection:
            operations = Operations(MigrationContext.configure(connection))
            board.op = operations
            moderation.op = operations
            # Batch operations reflect foreign-key targets, so provide minimal parents.
            connection.execute(text("CREATE TABLE users (id CHAR(32) PRIMARY KEY)"))
            connection.execute(text("CREATE TABLE teams (id CHAR(32) PRIMARY KEY)"))
            board.upgrade()
            live = _insert(connection, "Live note", deleted=False)
            by_manager = _insert(connection, "[Removed by manager]", deleted=True)
            by_author = _insert(connection, "[Removed by author]", deleted=True)

            moderation.upgrade()
            inspector = inspect(connection)
            assert "team_board_read_cursors" in inspector.get_table_names()
            columns = {column["name"] for column in inspector.get_columns("team_board_posts")}
            assert {"edited_at", "removal"} <= columns
            rows = dict(
                connection.execute(
                    text("SELECT id, removal || '|' || text FROM team_board_posts")
                ).all()
            )
            assert rows[by_manager] == "moderator|[Removed by a moderator]"
            assert rows[by_author] == "author|[Removed by author]"
            assert live not in rows or rows[live] is None
            with pytest.raises(IntegrityError), connection.begin_nested():
                connection.execute(
                    text("UPDATE team_board_posts SET removal = 'anyone' WHERE id = :id"),
                    {"id": live},
                )

            moderation.downgrade()
            inspector = inspect(connection)
            assert "team_board_read_cursors" not in inspector.get_table_names()
            columns = {column["name"] for column in inspector.get_columns("team_board_posts")}
            assert not {"edited_at", "removal"} & columns
            assert connection.execute(text("SELECT count(*) FROM team_board_posts")).scalar() == 3
    finally:
        engine.dispose()
