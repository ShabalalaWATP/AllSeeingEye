"""Conservative eligibility for the ordinary app's optional PostgreSQL template."""

from collections.abc import Callable
from hashlib import sha256
from inspect import unwrap
from typing import Any

from sqlalchemy import Connection
from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy.exc import CompileError
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.schema import CreateIndex, CreateTable

from ase.adapters.persistence.base import Base
from database_markers import file_constructs_database, uses_database

_DEFAULTS: dict[str, Callable[..., Any]] = {}
_METADATA = Base.metadata
DDL_EVENTS = ("before_create", "after_create", "before_drop", "after_drop")


def template_default(function: Callable[..., Any]) -> Callable[..., Any]:
    """Register exact ordinary fixture functions, including their unwrapped identity."""
    _DEFAULTS[function.__name__] = function
    return function


def ordinary_app(item: Any) -> bool:
    """Exclude overrides, special lanes and independently constructed databases."""
    if any(item.get_closest_marker(name) for name in ("postgres", "migration", "race")):
        return False
    definitions = getattr(getattr(item, "_fixtureinfo", None), "name2fixturedefs", {})
    for name in ("app", "settings"):
        candidates = definitions.get(name, ())
        if not candidates or unwrap(candidates[-1].func) is not _DEFAULTS.get(name):
            return False
    if file_constructs_database(item.path) or uses_database(getattr(item, "obj", None)):
        return False
    # This helper follows imported aliases/closures as well as direct factory names.
    exempt = {*_DEFAULTS, "template_database", "isolated_postgres_database"}
    return not any(
        uses_database(definition.func)
        for name, candidates in definitions.items()
        if name not in exempt
        for definition in candidates
    )


def schema_fingerprint() -> str | None:
    """Reject DDL callbacks and unsupported schema state, rather than caching effects."""
    metadata = Base.metadata
    if metadata is not _METADATA or metadata._sequences:  # Explicit SQLAlchemy sequences.
        return None
    objects: list[Any] = [metadata]
    for table in metadata.tables.values():
        if table.schema is not None:
            return None
        objects.extend((table, *table.columns, *table.constraints, *table.indexes))
        objects.extend(column.type for column in table.columns)
    for target in objects:
        dispatch = getattr(target, "dispatch", None)
        if any(tuple(getattr(dispatch, name, ())) for name in DDL_EVENTS):
            return None
    try:
        pg_dialect = dialect()
        statements = []
        for table in sorted(metadata.tables.values(), key=lambda value: value.name):
            statements.append(str(CreateTable(table).compile(dialect=pg_dialect)))
            statements.extend(
                str(CreateIndex(index).compile(dialect=pg_dialect))
                for index in sorted(table.indexes, key=lambda value: value.name or "")
            )
    except CompileError:
        return None
    return sha256("\n".join(statements).encode()).hexdigest()


def instrumented(engine: AsyncEngine) -> bool:
    """DDL-observing instrumentation needs the normal create/drop path.

    SQLAlchemy's pinned event dispatcher exposes inherited and instance listeners.
    Pool codec/initialisation listeners installed by SQLAlchemy itself remain valid;
    application/test listeners and all engine/dialect observers require fallback.
    A class-level Connection hook conservatively disables cloning for that process.
    Production ORM commit/rollback signalling is independent and stays untouched.
    """
    if getattr(Connection, "_has_events", False):
        return True
    for dispatch in (engine.sync_engine.dispatch, engine.dialect.dispatch):
        if any(tuple(getattr(dispatch, name)) for name in dispatch._event_names):
            return True
    pool = engine.sync_engine.pool.dispatch
    return any(
        name != "connect" or not _builtin_pool_connect(listener)
        for name in pool._event_names
        for listener in getattr(pool, name)
    )


def _builtin_pool_connect(listener: Any) -> bool:
    """Recognise only the pinned factory's two callbacks, including once wrappers."""
    name = getattr(listener, "__qualname__", "")
    if (
        getattr(listener, "__module__", "") == "sqlalchemy.util.langhelpers"
        and name == "only_once.<locals>.go"
    ):
        cells = dict(zip(listener.__code__.co_freevars, listener.__closure__, strict=True))
        callback = cells["fn"].cell_contents
        return (
            getattr(callback, "__module__", "") == "sqlalchemy.engine.create"
            and callback.__qualname__ == "create_engine.<locals>.first_connect"
        )
    if (
        getattr(listener, "__module__", "") != "sqlalchemy.engine.create"
        or name != "create_engine.<locals>.on_connect"
    ):
        return False
    cells = dict(zip(listener.__code__.co_freevars, listener.__closure__, strict=True))
    callback = cells["do_on_connect"].cell_contents
    return getattr(callback, "__module__", "").startswith("sqlalchemy.dialects.")
