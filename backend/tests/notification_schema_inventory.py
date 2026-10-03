"""Fresh physical schema inventories for explicitly owned native PostgreSQL fixtures.

Successful inventories equal the generic per-table witness. Any native reflection
error invalidates the entire snapshot and propagates without replay or savepoints;
the relative priority of multiple potential reflection failures is not promised.
"""

import re

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql.asyncpg import PGDialect_asyncpg
from sqlalchemy.dialects.postgresql.base import PGInspector
from sqlalchemy.engine.reflection import ObjectKind, ObjectScope

from notification_migration_helpers import schema_state

METHODS = {
    "columns": ("get_columns", "get_multi_columns"),
    "indexes": ("get_indexes", "get_multi_indexes"),
    "primary_key": ("get_pk_constraint", "get_multi_pk_constraint"),
    "foreign_keys": ("get_foreign_keys", "get_multi_foreign_keys"),
    "checks": ("get_check_constraints", "get_multi_check_constraints"),
    "unique": ("get_unique_constraints", "get_multi_unique_constraints"),
}
_NAMES = ("get_table_names", *(name for pair in METHODS.values() for name in pair))
_INSPECTOR_METHODS = {name: getattr(PGInspector, name) for name in _NAMES}
_DIALECT_METHODS = {name: getattr(PGDialect_asyncpg, name) for name in _NAMES}


def native_owned_inventory(connection, inspector):
    """Reject non-owned connections and custom/injected reflection implementations."""
    url = connection.engine.url
    if (
        connection.info.get("ase_owned_notification_migration") is not True
        or url.drivername != "postgresql+asyncpg"
        or url.host not in {"127.0.0.1", "localhost", "::1"}
        or url.query
        or not re.fullmatch(r"ase_notification_migration_[a-f0-9]{32}", url.database or "")
        or type(inspector) is not PGInspector
        or type(connection.dialect) is not PGDialect_asyncpg
        or inspector.bind is not connection
        or inspector.engine is not connection.engine
        or inspector.dialect is not connection.dialect
    ):
        return False
    return all(
        getattr(getattr(target, name), "__func__", None) is original
        and getattr(getattr(target, name), "__self__", None) is target
        for target, methods in (
            (inspector, _INSPECTOR_METHODS),
            (connection.dialect, _DIALECT_METHODS),
        )
        for name, original in methods.items()
    )


def batch_schema_state(connection, inspector, names):
    """Batch only complete maps; let reflection/SQL errors escape unchanged."""
    if not names:
        return {}
    expected = {(None, name) for name in names}
    maps = {
        key: getattr(inspector, multi)(
            filter_names=names, kind=ObjectKind.ANY, scope=ObjectScope.ANY
        )
        for key, (_single, multi) in METHODS.items()
    }
    if any(set(values) != expected for values in maps.values()):
        # No exception occurred: preserve the complete generic witness rather
        # than accepting partial maps. Retain the original names so a vanished
        # table raises instead of disappearing from a refreshed table-name list.
        return individual_known_names(connection, names)
    return {
        name: {
            "columns": [
                (column["name"], str(column["type"]), column["nullable"], column["default"])
                for column in maps["columns"][None, name]
            ],
            **{key: values[None, name] for key, values in maps.items() if key != "columns"},
        }
        for name in names
    }


def individual_known_names(connection, names):
    """Keep generic field semantics and per-table failure order for known names."""
    inspector = sa.inspect(connection)
    return {
        name: {
            "columns": [
                (column["name"], str(column["type"]), column["nullable"], column["default"])
                for column in inspector.get_columns(name)
            ],
            "indexes": inspector.get_indexes(name),
            "primary_key": inspector.get_pk_constraint(name),
            "foreign_keys": inspector.get_foreign_keys(name),
            "checks": inspector.get_check_constraints(name),
            "unique": inspector.get_unique_constraints(name),
        }
        for name in names
    }


def owned_schema_state(connection):
    """Opt owned migration callers in; leave generic/SQLite/error probes unchanged."""
    inspector = sa.inspect(connection)
    if not native_owned_inventory(connection, inspector):
        return schema_state(connection)
    return batch_schema_state(connection, inspector, inspector.get_table_names())
