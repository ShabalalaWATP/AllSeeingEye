"""Compare full fingerprints with the original uncached metadata/listener algorithm."""

from collections import deque
from hashlib import sha256
from types import SimpleNamespace

import pytest
from sqlalchemy import (
    Column,
    DefaultClause,
    Enum,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    event,
    text,
)
from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy.event.attr import _JoinedListener, _ListenerCollection
from sqlalchemy.exc import CompileError
from sqlalchemy.schema import CreateIndex, CreateTable
from sqlalchemy.types import UserDefinedType

import postgres_template_guard as guard

EVENTS = ("before_create", "after_create", "before_drop", "after_drop")


def original_fingerprint(metadata, expected_metadata):
    """Keep the full d078 algorithm as an oracle, independent of the candidate helper."""
    if metadata is not expected_metadata or metadata._sequences:
        return None
    objects = [metadata]
    for table in metadata.tables.values():
        if table.schema is not None:
            return None
        objects.extend((table, *table.columns, *table.constraints, *table.indexes))
        objects.extend(column.type for column in table.columns)
    for target in objects:
        dispatch = getattr(target, "dispatch", None)
        if any(tuple(getattr(dispatch, name, ())) for name in EVENTS):
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


def test_current_application_metadata_matches_complete_original_oracle():
    metadata = guard.Base.metadata
    assert metadata.tables
    expected = original_fingerprint(metadata, guard._METADATA)
    assert expected and guard.schema_fingerprint() == expected


@pytest.fixture
def metadata(monkeypatch):
    result = MetaData()
    Table("parent", result, Column("id", Integer, primary_key=True))
    child = Table(
        "child",
        result,
        Column("id", Integer, primary_key=True),
        Column("parent_id", Integer, ForeignKey("parent.id")),
        Column("name", String(20)),
        # Isolate explicit type listeners; automatic Enum DDL is checked separately.
        Column("status", Enum("ready", "done", name="child_status", _create_events=False)),
    )
    Index("ix_child_name", child.c.name)
    monkeypatch.setattr(guard, "Base", SimpleNamespace(metadata=result))
    monkeypatch.setattr(guard, "_METADATA", result)
    return result


@pytest.mark.parametrize(
    "change",
    [
        "nullable",
        "type_length",
        "default",
        "unique",
        "predicate",
        "foreign_key",
        "schema",
        "sequence",
    ],
)
def test_current_mutation_and_restoration_match_complete_oracle(metadata, monkeypatch, change):
    baseline = original_fingerprint(metadata, metadata)
    assert baseline and guard.schema_fingerprint() == baseline
    table = metadata.tables["child"]
    column = table.c.name
    index = next(iter(table.indexes))
    with monkeypatch.context() as patch:
        if change == "nullable":
            patch.setattr(column, "nullable", False)
        elif change == "type_length":
            patch.setattr(column.type, "length", 80)
        elif change == "default":
            patch.setattr(column, "server_default", DefaultClause(text("'changed'")))
        elif change == "unique":
            patch.setattr(index, "unique", True)
        elif change == "predicate":
            patch.setitem(index.dialect_options["postgresql"], "where", column.is_not(None))
        elif change == "foreign_key":
            patch.setattr(next(iter(table.foreign_key_constraints)), "ondelete", "CASCADE")
        elif change == "schema":
            patch.setattr(table, "schema", "changed")
        else:
            patch.setattr(metadata, "_sequences", {"changed": object()})
        changed = original_fingerprint(metadata, metadata)
        assert changed != baseline
        assert guard.schema_fingerprint() == changed
    assert original_fingerprint(metadata, metadata) == baseline
    assert guard.schema_fingerprint() == baseline


def test_new_table_and_metadata_replacement_are_not_cached(metadata, monkeypatch):
    baseline = guard.schema_fingerprint()
    added = Table("new_table", metadata, Column("id", Integer, primary_key=True))
    try:
        changed = original_fingerprint(metadata, metadata)
        assert changed != baseline and guard.schema_fingerprint() == changed
    finally:
        metadata.remove(added)
    assert guard.schema_fingerprint() == baseline
    with monkeypatch.context() as patch:
        replacement = MetaData()
        patch.setattr(guard.Base, "metadata", replacement)
        assert guard.schema_fingerprint() is None
        assert original_fingerprint(replacement, metadata) is None
    assert guard.schema_fingerprint() == baseline


def test_automatic_type_ddl_listeners_still_refuse_template_reuse(metadata):
    Table("enumerated", metadata, Column("state", Enum("ready", "done", name="state_type")))
    assert original_fingerprint(metadata, metadata) is None
    assert guard.schema_fingerprint() is None


@pytest.mark.parametrize("event_name", EVENTS)
@pytest.mark.parametrize(
    "target_name", ["metadata", "table", "column", "constraint", "index", "type"]
)
def test_each_ddl_target_and_event_matches_oracle_after_restoration(
    metadata, target_name, event_name
):
    table = metadata.tables["child"]
    target = {
        "metadata": metadata,
        "table": table,
        "column": table.c.name,
        "constraint": table.primary_key,
        "index": next(iter(table.indexes)),
        "type": table.c.status.type,
    }[target_name]
    baseline = guard.schema_fingerprint()

    def forbidden(*_args, **_kwargs):
        pytest.fail("DDL listeners must be inspected, never executed")

    event.listen(target, event_name, forbidden)
    try:
        assert original_fingerprint(metadata, metadata) is None
        assert guard.schema_fingerprint() is None
    finally:
        event.remove(target, event_name, forbidden)
    assert guard.schema_fingerprint() == original_fingerprint(metadata, metadata) == baseline


@pytest.mark.parametrize("error_type", [CompileError, RuntimeError])
def test_compiler_failure_retains_original_fallback_or_exception(metadata, monkeypatch, error_type):
    failure = error_type("synthetic compiler failure")

    class BrokenType(UserDefinedType):
        def get_col_spec(self, **_kwargs):
            raise failure

    monkeypatch.setattr(metadata.tables["child"].c.name, "type", BrokenType())
    if error_type is CompileError:
        assert guard.schema_fingerprint() is None
        assert original_fingerprint(metadata, metadata) is None
    else:
        for operation in (
            guard.schema_fingerprint,
            lambda: original_fingerprint(metadata, metadata),
        ):
            with pytest.raises(RuntimeError) as caught:
                operation()
            assert caught.value is failure


@pytest.mark.parametrize(
    "placement",
    ["joined_local", "joined_parent", "empty_parent", "collection_parent", "collection_local"],
)
@pytest.mark.parametrize("kind", ["unknown", "listener_subclass", "deque_subclass"])
@pytest.mark.parametrize("raises", [False, True])
def test_nested_untrusted_collections_preserve_complete_oracle(
    metadata, monkeypatch, placement, kind, raises
):
    failure = RuntimeError("nested listener iterator failure")

    def forbidden(*_args, **_kwargs):
        pytest.fail("A nested callback must never execute")

    class FalseLength:
        name = "before_create"

        def __len__(self):
            return 0

        def __iter__(self):
            yield forbidden
            if raises:
                raise failure

    class ListenerSubclass(FalseLength, _ListenerCollection):
        pass

    class DequeSubclass(FalseLength, deque):
        pass

    empty = metadata.dispatch.before_create
    if kind == "unknown":
        changed = FalseLength()
    elif kind == "listener_subclass":
        changed = ListenerSubclass(empty.parent, MetaData)
    else:
        changed = DequeSubclass()
    if placement.startswith("joined_"):
        parent = MetaData()
        target = metadata if placement == "joined_local" else parent
        monkeypatch.setattr(target.dispatch, "before_create", changed)
        joined = metadata.dispatch._join(parent.dispatch)
        assert type(joined.before_create) is _JoinedListener
        monkeypatch.setattr(metadata, "dispatch", joined)
    elif placement == "empty_parent":
        monkeypatch.setattr(empty, "parent_listeners", changed)
    else:
        listeners = empty.for_modify(metadata.dispatch)
        field = "parent_listeners" if placement == "collection_parent" else "listeners"
        monkeypatch.setattr(listeners, field, changed)
    for operation in (lambda: original_fingerprint(metadata, metadata), guard.schema_fingerprint):
        if raises:
            with pytest.raises(RuntimeError) as caught:
                operation()
            assert caught.value is failure
        else:
            assert operation() is None
