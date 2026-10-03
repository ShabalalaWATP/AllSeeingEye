"""The owned batch witnesses the physical schema, including real constraint behaviour."""

import pytest
import sqlalchemy as sa

from notification_migration_helpers import (
    migration_database as migration_database,  # noqa: PLC0414
)
from notification_migration_helpers import schema_state
from notification_schema_inventory import native_owned_inventory, owned_schema_state
from test_notification_reflection import (
    reflection_database as reflection_database,  # noqa: PLC0414
)

pytestmark = pytest.mark.db


def physical_schema(connection):
    if connection.dialect.name == "sqlite":
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
    metadata = sa.MetaData()
    parent = sa.Table(
        "Inventory Parent",
        metadata,
        sa.Column("second", sa.Integer),
        sa.Column("first", sa.Integer),
        sa.PrimaryKeyConstraint("first", "second", name="parent_pk"),
        sa.UniqueConstraint("second", "first", name="parent_reverse_unique"),
    )
    child = sa.Table(
        "inventory_child",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("left", sa.Integer),
        sa.Column("right", sa.Integer),
        sa.Column("label", sa.String(80), nullable=False, server_default="draft"),
        sa.Column("score", sa.Integer, server_default="0"),
        sa.Column("identifier", sa.Uuid(), nullable=True),
        sa.Column("state", sa.Enum("new", "seen", name="inventory_status"), server_default="new"),
        sa.ForeignKeyConstraint(
            ["left", "right"],
            ["Inventory Parent.second", "Inventory Parent.first"],
            name="child_parent",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("label", "score", name="child_label_score"),
        sa.CheckConstraint("score >= 0", name="nonnegative_score"),
    )
    sa.Index(
        "child_score_partial",
        child.c.score,
        postgresql_where=child.c.score > 0,
        sqlite_where=child.c.score > 0,
    )
    if connection.dialect.name == "postgresql":
        sa.Index("child_label_expression", sa.func.lower(child.c.label))
    metadata.create_all(connection)
    connection.execute(parent.insert().values(first=1, second=2))
    connection.execute(child.insert().values(id=1, left=2, right=1, label="first", score=1))
    return parent, child


def comparable(value):
    # SQLite represents its partial-index predicate as a new TextClause per call.
    if isinstance(value, sa.sql.elements.TextClause):
        return str(value)
    if isinstance(value, dict):
        return {key: comparable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [comparable(item) for item in value]
    return value


def assert_physical_parity(connection):
    original = comparable(schema_state(connection))
    current = comparable(owned_schema_state(connection))
    assert list(current) == list(original)
    assert current == original
    return current


async def test_owned_native_and_generic_sqlite_inventories_match_all_physical_fields(
    reflection_database,
):
    def check(connection):
        physical_schema(connection)
        assert native_owned_inventory(connection, sa.inspect(connection)) is (
            connection.dialect.name == "postgresql"
        )
        result = assert_physical_parity(connection)
        child = result["inventory_child"]
        assert child["primary_key"]["constrained_columns"] == ["id"]
        assert child["foreign_keys"][0]["constrained_columns"] == ["left", "right"]
        assert child["foreign_keys"][0]["referred_columns"] == ["second", "first"]
        assert child["checks"][0]["name"] == "nonnegative_score"
        assert any(index["name"] == "child_score_partial" for index in child["indexes"])
        assert child["unique"][0]["column_names"] == ["label", "score"]
        assert next(column for column in child["columns"] if column[0] == "label")[2] is False

    await reflection_database.run(check)


async def test_complete_current_migrated_schema_has_exact_physical_parity(reflection_database):
    await reflection_database.migrate("head")

    def check(connection):
        result = assert_physical_parity(connection)
        assert len(result) > 80

    await reflection_database.run(check)


async def test_later_calls_see_columns_indexes_and_constraints_after_ddl(reflection_database):
    def check(connection):
        physical_schema(connection)
        before = assert_physical_parity(connection)
        connection.exec_driver_sql("ALTER TABLE inventory_child ADD COLUMN memo VARCHAR(30)")
        connection.exec_driver_sql("CREATE INDEX memo_index ON inventory_child (memo)")
        added = assert_physical_parity(connection)
        assert added != before
        assert any(column[0] == "memo" for column in added["inventory_child"]["columns"])
        connection.exec_driver_sql("DROP INDEX memo_index")
        connection.exec_driver_sql("ALTER TABLE inventory_child DROP COLUMN memo")
        assert assert_physical_parity(connection) == before
        if connection.dialect.name == "postgresql":
            connection.exec_driver_sql(
                "ALTER TABLE inventory_child DROP CONSTRAINT nonnegative_score"
            )
            assert assert_physical_parity(connection)["inventory_child"]["checks"] == []

    await reflection_database.run(check)


async def test_native_constraints_and_savepoint_recovery_remain_real(reflection_database):
    def check(connection):
        parent, child = physical_schema(connection)
        original = assert_physical_parity(connection)
        for values in (
            {"id": 2, "left": 99, "right": 98, "label": "foreign", "score": 2},
            {"id": 2, "left": 2, "right": 1, "label": "first", "score": 1},
            {"id": 2, "left": 2, "right": 1, "label": "negative", "score": -1},
        ):
            with pytest.raises(sa.exc.IntegrityError), connection.begin_nested():
                connection.execute(child.insert().values(**values))
        connection.execute(child.insert().values(id=2, left=2, right=1, label="valid", score=2))
        assert connection.scalar(sa.select(sa.func.count()).select_from(child)) == 2
        assert assert_physical_parity(connection) == original
        connection.execute(parent.delete())
        assert connection.scalar(sa.select(sa.func.count()).select_from(child)) == 0

    await reflection_database.run(check)
