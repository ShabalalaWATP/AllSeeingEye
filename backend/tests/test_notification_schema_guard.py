"""The physical-inventory fast path requires native methods and transient ownership."""

from types import SimpleNamespace

import pytest
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql.asyncpg import PGDialect_asyncpg
from sqlalchemy.dialects.postgresql.base import PGInspector

import notification_migration_helpers as helpers
import notification_schema_inventory as inventory

KEY = "ase_owned_notification_migration"


def native_pair():
    connection = SimpleNamespace(
        engine=SimpleNamespace(
            url=sa.make_url("postgresql+asyncpg://localhost/ase_notification_migration_" + "a" * 32)
        ),
        dialect=PGDialect_asyncpg(),
        info={KEY: True},
    )
    inspector = PGInspector.__new__(PGInspector)
    inspector.bind = connection
    inspector.engine = connection.engine
    inspector.dialect = connection.dialect
    return connection, inspector


def test_exact_native_pair_is_eligible_and_absent_ownership_is_not():
    connection, inspector = native_pair()
    assert inventory.native_owned_inventory(connection, inspector)
    connection.info.clear()
    assert not inventory.native_owned_inventory(connection, inspector)


@pytest.mark.parametrize("attribute", ["bind", "engine", "dialect"])
def test_inspector_must_belong_to_the_exact_connection(attribute):
    connection, inspector = native_pair()
    other_connection, other_inspector = native_pair()
    assert other_connection is not connection
    setattr(inspector, attribute, getattr(other_inspector, attribute))
    assert not inventory.native_owned_inventory(connection, inspector)


@pytest.mark.parametrize("target", ["inspector", "dialect"])
@pytest.mark.parametrize("method", ["get_columns", "get_multi_columns", "get_table_names"])
def test_original_methods_rebound_from_another_native_instance_are_excluded(target, method):
    connection, inspector = native_pair()
    other_connection, other_inspector = native_pair()
    receiver = inspector if target == "inspector" else connection.dialect
    other = other_inspector if target == "inspector" else other_connection.dialect
    setattr(receiver, method, getattr(other, method))
    assert not inventory.native_owned_inventory(connection, inspector)


@pytest.mark.parametrize(
    "url",
    [
        "sqlite+aiosqlite://",
        "postgresql+psycopg://localhost/ase_notification_migration_" + "a" * 32,
        "postgresql+asyncpg://remote.example/ase_notification_migration_" + "a" * 32,
        "postgresql+asyncpg://localhost/operator_database",
        "postgresql+asyncpg://localhost/ase_notification_migration_" + "g" * 32,
        "postgresql+asyncpg://localhost/ase_notification_migration_" + "a" * 32 + "?host=other",
    ],
)
def test_non_native_or_unowned_effective_urls_are_excluded(url):
    connection, inspector = native_pair()
    connection.engine.url = sa.make_url(url)
    assert not inventory.native_owned_inventory(connection, inspector)


@pytest.mark.parametrize("target", ["inspector", "dialect"])
@pytest.mark.parametrize("method", ["get_columns", "get_multi_columns", "get_table_names"])
@pytest.mark.parametrize("class_override", [False, True])
def test_instance_and_class_reflection_overrides_keep_original_path(
    monkeypatch, target, method, class_override
):
    connection, inspector = native_pair()
    overridden = inspector if target == "inspector" else connection.dialect
    monkeypatch.setattr(type(overridden) if class_override else overridden, method, lambda *_a: {})
    assert not inventory.native_owned_inventory(connection, inspector)
    sentinel = object()
    monkeypatch.setattr(inventory.sa, "inspect", lambda _connection: inspector)
    monkeypatch.setattr(
        inventory, "schema_state", lambda actual: sentinel if actual is connection else None
    )
    assert inventory.owned_schema_state(connection) is sentinel


def test_custom_inspector_subclass_is_not_native():
    class CustomInspector(PGInspector):
        pass

    connection, _inspector = native_pair()
    assert not inventory.native_owned_inventory(
        connection, CustomInspector.__new__(CustomInspector)
    )


def test_empty_inventory_never_calls_reflection_or_fallback():
    class NoMethods:
        def __getattr__(self, name):
            pytest.fail(f"Empty schema unexpectedly requested {name}")

    assert inventory.batch_schema_state(None, NoMethods(), []) == {}


@pytest.mark.parametrize("existing", [None, False, "previous owner"])
@pytest.mark.parametrize("raises", [False, True])
async def test_ownership_is_restored_after_success_or_failure(monkeypatch, existing, raises):
    information = {} if existing is None else {KEY: existing}
    disposed = []

    class Connection:
        sync_connection = SimpleNamespace(info=information)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        async def run_sync(self, action, *args):
            return action(self.sync_connection, *args)

    class Engine:
        def begin(self):
            return Connection()

        async def dispose(self):
            disposed.append(True)

    def observe(connection):
        assert connection.info[KEY] is True
        if raises:
            raise ValueError("controlled callback failure")
        return "observed"

    monkeypatch.setattr(helpers, "create_async_engine", lambda _url: Engine())
    database = helpers.MigrationDatabase("sqlite+aiosqlite://", owns_postgres=True)
    if raises:
        with pytest.raises(ValueError, match="controlled callback failure"):
            await database.run(observe)
    else:
        assert await database.run(observe) == "observed"
    assert information == ({} if existing is None else {KEY: existing})
    assert disposed == [True]


@pytest.mark.parametrize("existing", [None, False, "previous owner"])
async def test_failed_callback_cannot_mask_original_error_by_reopening_info(monkeypatch, existing):
    information = {} if existing is None else {KEY: existing}
    disposed = []
    original = ValueError("controlled connection closure")

    class SyncConnection:
        inaccessible = False

        @property
        def info(self):
            if self.inaccessible:
                pytest.fail("Cleanup tried to access an unusable connection")
            return information

    class Connection:
        sync_connection = SyncConnection()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        async def run_sync(self, action, *args):
            return action(self.sync_connection, *args)

    class Engine:
        def begin(self):
            return Connection()

        async def dispose(self):
            disposed.append(True)

    def fail(connection):
        assert connection.info[KEY] is True
        connection.inaccessible = True
        raise original

    monkeypatch.setattr(helpers, "create_async_engine", lambda _url: Engine())
    with pytest.raises(ValueError) as failure:
        await helpers.MigrationDatabase("sqlite+aiosqlite://", owns_postgres=True).run(fail)
    assert failure.value is original
    assert information == ({} if existing is None else {KEY: existing})
    assert disposed == [True]
