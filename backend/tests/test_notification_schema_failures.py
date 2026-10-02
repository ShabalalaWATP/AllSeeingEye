"""Native inventory errors abort their snapshot without replay or hidden omissions."""

from types import SimpleNamespace

import pytest
import sqlalchemy as sa

import notification_schema_inventory as inventory
from notification_migration_helpers import (
    migration_database as migration_database,  # noqa: PLC0414
)
from notification_migration_helpers import schema_state

pytestmark = [pytest.mark.db, pytest.mark.postgres]


def reflected_proxy(connection):
    inspector = sa.inspect(connection)
    return SimpleNamespace(
        **{multi: getattr(inspector, multi) for _single, multi in inventory.METHODS.values()}
    )


def seed(connection):
    connection.exec_driver_sql("CREATE TABLE inventory_a (id INTEGER PRIMARY KEY)")
    connection.exec_driver_sql("CREATE TABLE inventory_b (id INTEGER PRIMARY KEY)")
    return ["inventory_a", "inventory_b"]


async def test_native_sql_error_is_original_transaction_stays_aborted_and_no_replay(
    migration_database, monkeypatch
):
    captured = []

    def forbidden(*_args):
        pytest.fail("A native reflection failure must not replay the individual path")

    monkeypatch.setattr(inventory, "individual_known_names", forbidden)

    def check(connection):
        names = seed(connection)
        proxy = reflected_proxy(connection)

        def fail_in_database(**_kwargs):
            try:
                connection.exec_driver_sql("SELECT 1 / 0")
            except sa.exc.DBAPIError as error:
                captured.append(error)
                raise

        proxy.get_multi_indexes = fail_in_database
        with pytest.raises(sa.exc.DBAPIError) as failure:
            inventory.batch_schema_state(connection, proxy, names)
        assert failure.value is captured[0]
        assert failure.value.orig.sqlstate == "22012"
        with pytest.raises(sa.exc.DBAPIError) as aborted:
            connection.exec_driver_sql("SELECT 1")
        assert aborted.value.orig.sqlstate == "25P02"
        # The existing outer transaction manager performs the rollback.
        raise failure.value

    with pytest.raises(sa.exc.DBAPIError) as propagated:
        await migration_database.run(check)
    assert propagated.value is captured[0]
    assert (
        await migration_database.run(lambda connection: connection.scalar(sa.text("SELECT 1"))) == 1
    )


@pytest.mark.parametrize("extra", [False, True])
async def test_incomplete_or_extra_maps_recover_complete_known_table_witness(
    migration_database, extra
):
    def check(connection):
        names = seed(connection)
        expected = schema_state(connection)
        proxy = reflected_proxy(connection)
        original = proxy.get_multi_columns

        def changed(**kwargs):
            result = original(**kwargs)
            if extra:
                result[None, "unexpected_table"] = []
            else:
                result.pop((None, names[0]))
            return result

        proxy.get_multi_columns = changed
        assert inventory.batch_schema_state(connection, proxy, names) == expected

    await migration_database.run(check)


async def test_vanished_requested_table_is_not_hidden_by_refreshed_name_list(migration_database):
    def check(connection):
        names = seed(connection)
        connection.exec_driver_sql("DROP TABLE inventory_b")
        with pytest.raises(sa.exc.NoSuchTableError, match="inventory_b"):
            inventory.batch_schema_state(connection, reflected_proxy(connection), names)

    await migration_database.run(check)


@pytest.mark.parametrize("operation", ["close", "invalidate"])
async def test_unusable_connection_retains_callback_error_and_clears_ownership(
    migration_database, operation
):
    original = ValueError("controlled native connection failure")
    captured = []

    def fail(connection):
        information = connection.info
        assert information["ase_owned_notification_migration"] is True
        captured.append(information)
        getattr(connection, operation)()
        raise original

    with pytest.raises(ValueError) as failure:
        await migration_database.run(fail)
    assert failure.value is original
    assert "ase_owned_notification_migration" not in captured[0]
    assert (
        await migration_database.run(lambda connection: connection.scalar(sa.text("SELECT 1"))) == 1
    )
