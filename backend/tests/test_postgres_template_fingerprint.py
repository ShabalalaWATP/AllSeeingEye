"""Each fingerprint compiles current metadata with a fresh PostgreSQL dialect."""

from hashlib import sha256
from types import SimpleNamespace

import pytest
from sqlalchemy import Column, DefaultClause, Index, Integer, MetaData, String, Table, event, text
from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy.schema import CreateIndex, CreateTable

import postgres_template_guard as guard


@pytest.fixture
def metadata(monkeypatch):
    result = MetaData()
    table = Table(
        "example", result, Column("id", Integer, primary_key=True), Column("name", String(20))
    )
    Index("ix_example_name", table.c.name)
    monkeypatch.setattr(guard, "Base", SimpleNamespace(metadata=result))
    monkeypatch.setattr(guard, "_METADATA", result)
    return result


def independently_compiled(metadata):
    statements = []
    for table in sorted(metadata.tables.values(), key=lambda value: value.name):
        statements.append(str(CreateTable(table).compile(dialect=dialect())))
        statements.extend(
            str(CreateIndex(index).compile(dialect=dialect()))
            for index in sorted(table.indexes, key=lambda value: value.name or "")
        )
    return sha256("\n".join(statements).encode()).hexdigest()


def test_dialect_is_fresh_per_call_and_never_hides_type_mutation(metadata, monkeypatch):
    instances = []

    def fresh():
        result = dialect()
        instances.append(result)
        return result

    monkeypatch.setattr(guard, "dialect", fresh)
    original = guard.schema_fingerprint()
    assert original == independently_compiled(metadata)
    assert len(instances) == 1
    metadata.tables["example"].c.name.type.length = 80
    changed = guard.schema_fingerprint()
    assert changed != original and changed == independently_compiled(metadata)
    assert len(instances) == 2 and instances[0] is not instances[1]


@pytest.mark.parametrize("mutation", ["nullable", "type", "default", "unique", "predicate"])
def test_current_column_and_index_changes_match_independent_compilation(metadata, mutation):
    original = guard.schema_fingerprint()
    column = metadata.tables["example"].c.name
    index = next(iter(column.table.indexes))
    if mutation == "nullable":
        column.nullable = not column.nullable
    elif mutation == "type":
        column.type = Integer()
    elif mutation == "default":
        column.server_default = DefaultClause(text("'example'"))
    elif mutation == "unique":
        index.unique = True
    else:
        index.dialect_options["postgresql"]["where"] = column.is_not(None)
    changed = guard.schema_fingerprint()
    assert changed != original and changed == independently_compiled(metadata)


@pytest.mark.parametrize("target_name", ["metadata", "table", "column", "index", "constraint"])
@pytest.mark.parametrize("event_name", guard.DDL_EVENTS)
def test_ddl_observers_still_reject_template_reuse(metadata, target_name, event_name):
    table = metadata.tables["example"]
    target = {
        "metadata": metadata,
        "table": table,
        "column": table.c.name,
        "index": next(iter(table.indexes)),
        "constraint": table.primary_key,
    }[target_name]
    original = guard.schema_fingerprint()

    def forbidden(*_args, **_kwargs):
        pytest.fail("Fingerprint compilation must not execute DDL observers")

    event.listen(target, event_name, forbidden)
    try:
        assert guard.schema_fingerprint() is None
    finally:
        event.remove(target, event_name, forbidden)
    assert guard.schema_fingerprint() == original
