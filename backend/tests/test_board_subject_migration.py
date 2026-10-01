"""Migration 0075 adds optional typed board subjects and removes them losslessly for posts."""

from __future__ import annotations

from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy.exc import IntegrityError

from ase.adapters.persistence.base import Base
from ase.infrastructure.migrations import alembic_config

SUBJECT_COLUMNS = {"subject_kind", "subject_id", "subject_version"}


def _insert(connection: sa.Connection, **values: object) -> str:
    post_id = uuid4().hex
    row = {
        "id": post_id,
        "team": uuid4().hex,
        "author": uuid4().hex,
        "kind": None,
        "subject": None,
        "version": None,
        "parent": None,
        **values,
    }
    connection.execute(
        sa.text(
            "INSERT INTO team_board_posts (id, team_id, author_id, text, created_at, updated_at,"
            " is_pinned, revision, parent_id, subject_kind, subject_id, subject_version)"
            " VALUES (:id, :team, :author, 'Note', '2026-10-01', '2026-10-01', 0, 1, :parent,"
            " :kind, :subject, :version)"
        ),
        row,
    )
    return post_id


def _columns(engine: sa.Engine) -> set[str]:
    return {column["name"] for column in sa.inspect(engine).get_columns("team_board_posts")}


def test_board_subject_migration_round_trip_on_sqlite(tmp_path) -> None:  # type: ignore[no-untyped-def]
    database = tmp_path / "board-subjects-disposable.db"
    config = alembic_config(f"sqlite+aiosqlite:///{database}")
    command.upgrade(config, "0066")
    engine = sa.create_engine(f"sqlite:///{database}")
    try:
        with engine.begin() as connection:
            connection.execute(
                sa.text(
                    "INSERT INTO team_board_posts (id, team_id, author_id, text, created_at,"
                    " updated_at, is_pinned, revision) VALUES (:id, :team, :author, 'Old',"
                    " '2026-09-30', '2026-09-30', 0, 1)"
                ),
                {"id": uuid4().hex, "team": uuid4().hex, "author": uuid4().hex},
            )
        command.upgrade(config, "0075")
        assert _columns(engine) >= SUBJECT_COLUMNS
        indexes = {index["name"] for index in sa.inspect(engine).get_indexes("team_board_posts")}
        assert "ix_team_board_posts_subject" in indexes
        with engine.begin() as connection:
            connection.execute(sa.text("PRAGMA foreign_keys=OFF"))
            parent = _insert(connection, kind="report_version", subject=uuid4().hex, version=2)
            _insert(connection, kind="saved_area", subject=uuid4().hex)
            _insert(connection, kind="drawing_collection", subject=uuid4().hex)
            assert (
                connection.execute(
                    sa.text("SELECT count(*) FROM team_board_posts WHERE subject_kind IS NULL")
                ).scalar()
                == 1
            )
            invalid = (
                {"kind": "report_version", "subject": uuid4().hex},
                {"kind": "saved_area", "subject": uuid4().hex, "version": 1},
                {"kind": "evidence", "subject": uuid4().hex},
                {"kind": "saved_area"},
                {"subject": uuid4().hex},
                {"version": 1},
                {"kind": "saved_area", "subject": uuid4().hex, "parent": parent},
            )
            for values in invalid:
                with pytest.raises(IntegrityError), connection.begin_nested():
                    _insert(connection, **values)
            context = MigrationContext.configure(
                connection,
                opts={
                    "include_object": lambda obj, name, kind, reflected, compare: (
                        (kind != "table" or name == "team_board_posts")
                        and (
                            kind == "table"
                            or getattr(obj, "table", None) is None
                            or obj.table.name == "team_board_posts"
                        )
                    )
                },
            )
            assert compare_metadata(context, Base.metadata) == []
        command.downgrade(config, "0066")
        assert not SUBJECT_COLUMNS & _columns(engine)
        with engine.connect() as connection:
            assert (
                connection.execute(sa.text("SELECT count(*) FROM team_board_posts")).scalar() == 4
            )
    finally:
        engine.dispose()
