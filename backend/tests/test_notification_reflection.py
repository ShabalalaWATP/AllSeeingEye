"""Historical snapshots inspect fresh target columns without loading related tables."""

from datetime import UTC

import pytest
import sqlalchemy as sa

from notification_migration_helpers import (
    NOW,
    MigrationDatabase,
    insert_row,
    schema_state,
    snapshot,
    table,
)
from notification_migration_helpers import (
    migration_database as migration_database,  # noqa: PLC0414
)

pytestmark = pytest.mark.db


@pytest.fixture(params=["sqlite", pytest.param("postgres", marks=pytest.mark.postgres)])
def reflection_database(request, tmp_path):
    if request.param == "postgres":
        return request.getfixturevalue("migration_database")
    return MigrationDatabase(f"sqlite+aiosqlite:///{(tmp_path / 'reflection.db').as_posix()}")


def seed(connection):
    metadata = sa.MetaData()
    sa.Table("reflection_parent", metadata, sa.Column("id", sa.Integer, primary_key=True))
    sa.Table(
        "reflection_child",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("position", sa.Integer, primary_key=True),
        sa.Column(
            "parent_id",
            sa.Integer,
            sa.ForeignKey("reflection_parent.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("payload", sa.JSON, nullable=False),
    )
    if connection.dialect.name == "sqlite":
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
    metadata.create_all(connection)
    insert_row(connection, "reflection_parent", id=1)
    for identity, position in ((2, 1), (1, 2)):
        insert_row(
            connection,
            "reflection_child",
            id=identity,
            position=position,
            parent_id=1,
            observed_at=NOW,
            payload={"retained": [identity]},
        )


def assert_target_reflection_and_constraints(connection):
    seed(connection)
    child = table(connection, "reflection_child")
    assert set(child.metadata.tables) == {"reflection_child"}
    assert {key.target_fullname for key in child.foreign_keys} == {"reflection_parent.id"}
    state = schema_state(connection)["reflection_child"]
    assert state["primary_key"]["constrained_columns"] == ["id", "position"]
    assert state["foreign_keys"][0]["options"]["ondelete"] == "CASCADE"
    rows = snapshot(connection, ["reflection_child"])["reflection_child"]
    assert [(row["id"], row["position"]) for row in rows] == [(1, 2), (2, 1)]
    assert rows[0]["payload"] == {"retained": [1]}
    assert rows[0]["active"] is True
    assert rows[0]["observed_at"].replace(tzinfo=UTC) == NOW
    with pytest.raises(sa.exc.IntegrityError), connection.begin_nested():
        connection.execute(
            child.insert().values(id=3, position=1, parent_id=404, observed_at=NOW, payload={})
        )
    assert snapshot(connection, ["reflection_child"])["reflection_child"] == rows
    parent = table(connection, "reflection_parent")
    connection.execute(parent.delete().where(parent.c.id == 1))
    assert snapshot(connection, ["reflection_child"])["reflection_child"] == []


async def test_target_reflection_preserves_typed_rows_and_native_constraints(reflection_database):
    await reflection_database.run(assert_target_reflection_and_constraints)


def assert_reflection_is_fresh_after_schema_change(connection):
    seed(connection)
    previous_schema = schema_state(connection)["reflection_child"]
    previous_rows = snapshot(connection, ["reflection_child"])["reflection_child"]
    connection.exec_driver_sql("ALTER TABLE reflection_child ADD COLUMN note VARCHAR(40)")
    changed = table(connection, "reflection_child")
    connection.execute(changed.update().where(changed.c.id == 1).values(note="New column"))
    current_schema = schema_state(connection)["reflection_child"]
    current_rows = snapshot(connection, ["reflection_child"])["reflection_child"]
    assert [column[0] for column in current_schema["columns"]] == [
        *(column[0] for column in previous_schema["columns"]),
        "note",
    ]
    assert current_schema["foreign_keys"] == previous_schema["foreign_keys"]
    assert current_schema["primary_key"] == previous_schema["primary_key"]
    assert [row["note"] for row in current_rows] == ["New column", None]
    assert [{key: row[key] for key in previous_rows[0]} for row in current_rows] == previous_rows


async def test_schema_and_rows_are_reflected_afresh_after_ddl(reflection_database):
    await reflection_database.run(assert_reflection_is_fresh_after_schema_change)
