"""Batched historical snapshots preserve rows, conversion hooks and strict failures."""

from collections import Counter
from contextlib import contextmanager
from uuid import uuid4

import pytest
import sqlalchemy as sa

from notification_migration_helpers import (
    migration_database as migration_database,  # noqa: PLC0414
)
from notification_migration_helpers import seed_legacy, snapshot, table
from test_notification_reflection import (
    reflection_database as reflection_database,  # noqa: PLC0414
)
from test_notification_reflection import seed

pytestmark = pytest.mark.db

NAMES = ("reflection_child", "reflection_parent", "reflection_reordered")


def individual_snapshot(connection, names):
    result = {}
    for name in names:
        target = table(connection, name)
        query = sa.select(target).order_by(*target.primary_key.columns)
        result[name] = [dict(row) for row in connection.execute(query).mappings()]
    return result


def assert_identical(actual, expected):
    assert actual == expected
    assert list(actual) == list(expected)
    for name, rows in actual.items():
        assert [list(row) for row in rows] == [list(row) for row in expected[name]]


def seed_reordered(connection):
    seed(connection)
    reordered = sa.Table(
        "reflection_reordered",
        sa.MetaData(),
        sa.Column("id", sa.Integer),
        sa.Column("position", sa.Integer),
        sa.PrimaryKeyConstraint("position", "id"),
    )
    reordered.create(connection)
    connection.execute(reordered.insert(), [{"id": 1, "position": 2}, {"id": 2, "position": 1}])


@pytest.mark.parametrize(
    "names",
    [NAMES, tuple(reversed(NAMES)), ("reflection_child",), (), (*NAMES, NAMES[0])],
    ids=["child-first", "parent-first", "child-only", "empty", "duplicate"],
)
async def test_requested_snapshots_match_individual_rows_and_key_order(reflection_database, names):
    def check(connection):
        seed_reordered(connection)
        expected = individual_snapshot(connection, names)
        actual = snapshot(connection, iter(names))
        assert_identical(actual, expected)
        if "reflection_reordered" in actual:
            assert [row["id"] for row in actual["reflection_reordered"]] == [2, 1]

    await reflection_database.run(check)


@contextmanager
def uuid_conversion():
    observed = []

    def convert(inspector, target, column):
        observed.append((target.name, column["name"]))
        if (
            inspector.bind.dialect.name == "sqlite"
            and isinstance(column["type"], sa.CHAR)
            and column["type"].length == 32
        ):
            column["type"] = sa.Uuid()

    sa.event.listen(sa.MetaData, "column_reflect", convert)
    try:
        yield observed
    finally:
        sa.event.remove(sa.MetaData, "column_reflect", convert)


async def test_conversion_callbacks_and_uuid_values_match_individual_reflection(
    reflection_database,
):
    def check(connection):
        seed_reordered(connection)
        target = sa.Table(
            "reflection_uuid", sa.MetaData(), sa.Column("id", sa.Uuid(), primary_key=True)
        )
        target.create(connection)
        identity = uuid4()
        connection.execute(target.insert().values(id=identity))
        names = (*NAMES, target.name)
        with uuid_conversion() as observed:
            expected = individual_snapshot(connection, names)
            expected_callbacks = Counter(observed)
            observed.clear()
            actual = snapshot(connection, names)
            assert Counter(observed) == expected_callbacks
        assert_identical(actual, expected)
        assert actual[target.name] == [{"id": identity}]

    await reflection_database.run(check)


async def test_complete_historical_snapshot_matches_individual_reflection(reflection_database):
    await reflection_database.migrate("head")

    def check(connection):
        with uuid_conversion():
            seed_legacy(connection)
            names = sa.inspect(connection).get_table_names()
            assert len(names) > 80
            assert_identical(snapshot(connection, names), individual_snapshot(connection, names))

    await reflection_database.run(check)


async def test_repeated_snapshots_see_added_and_removed_schema_and_rows(reflection_database):
    def check(connection):
        seed_reordered(connection)
        before = snapshot(connection, NAMES)
        connection.exec_driver_sql("ALTER TABLE reflection_child ADD COLUMN note VARCHAR(40)")
        child = table(connection, "reflection_child")
        connection.execute(child.update().where(child.c.id == 1).values(note="Added column"))
        changed = snapshot(connection, NAMES)
        assert changed["reflection_child"][0]["note"] == "Added column"
        assert "note" not in before["reflection_child"][0]
        connection.exec_driver_sql("ALTER TABLE reflection_child DROP COLUMN note")
        child = table(connection, "reflection_child")
        connection.execute(child.delete().where(child.c.id == 1))
        final = snapshot(connection, NAMES)
        assert final["reflection_child"] == [before["reflection_child"][1]]
        assert_identical(final, individual_snapshot(connection, NAMES))

    await reflection_database.run(check)


@pytest.mark.parametrize("missing_first", [True, False])
@pytest.mark.parametrize("callback_failure", [True, False])
async def test_missing_table_and_callback_errors_keep_original_order(
    reflection_database, missing_first, callback_failure
):
    def check(connection):
        seed_reordered(connection)
        names = ["reflection_parent", "absent_snapshot_target"]
        if missing_first:
            names.reverse()

        def reject(_inspector, _target, _column):
            if callback_failure:
                raise sa.exc.InvalidRequestError("unrelated conversion failure")

        sa.event.listen(sa.MetaData, "column_reflect", reject)
        try:
            with pytest.raises(sa.exc.InvalidRequestError) as expected:
                individual_snapshot(connection, names)
            with pytest.raises(type(expected.value)) as actual:
                snapshot(connection, names)
            assert str(actual.value) == str(expected.value)
        finally:
            sa.event.remove(sa.MetaData, "column_reflect", reject)

    await reflection_database.run(check)


@pytest.mark.parametrize("transient", [False, True])
async def test_unreflectable_table_cannot_silently_disappear(reflection_database, transient):
    def check(connection):
        seed_reordered(connection)
        calls = 0

        def reject(_inspector, target, _column):
            nonlocal calls
            if target.name == "reflection_parent":
                calls += 1
                if not transient or calls == 1:
                    raise sa.exc.UnreflectableTableError("unreadable parent shape")

        sa.event.listen(sa.MetaData, "column_reflect", reject)
        try:
            with (
                pytest.warns(sa.exc.SAWarning, match="Skipping table reflection_parent"),
                pytest.raises(sa.exc.UnreflectableTableError),
            ):
                snapshot(connection, ("reflection_parent", "reflection_child"))
        finally:
            sa.event.remove(sa.MetaData, "column_reflect", reject)

    await reflection_database.run(check)


async def test_unrelated_callback_failure_propagates_from_valid_batch(reflection_database):
    def check(connection):
        seed_reordered(connection)
        sentinel = sa.exc.InvalidRequestError("conversion must remain visible")

        def reject(_inspector, _target, _column):
            raise sentinel

        sa.event.listen(sa.MetaData, "column_reflect", reject)
        try:
            with pytest.raises(sa.exc.InvalidRequestError) as actual:
                snapshot(connection, NAMES)
            assert actual.value is sentinel
        finally:
            sa.event.remove(sa.MetaData, "column_reflect", reject)

    await reflection_database.run(check)


async def test_view_and_temporary_table_keep_individual_reflection_support(reflection_database):
    def check(connection):
        seed_reordered(connection)
        connection.exec_driver_sql(
            "CREATE VIEW reflection_view AS SELECT id FROM reflection_parent"
        )
        connection.exec_driver_sql(
            "CREATE TEMPORARY TABLE reflection_temp (id INTEGER PRIMARY KEY)"
        )
        connection.exec_driver_sql("INSERT INTO reflection_temp (id) VALUES (2), (1)")
        names = ("reflection_view", "reflection_temp", "reflection_parent")
        assert_identical(snapshot(connection, names), individual_snapshot(connection, names))

    await reflection_database.run(check)
