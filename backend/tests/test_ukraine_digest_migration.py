"""Migration 0057 creates the bounded Ukraine digest history and removes it cleanly."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect

VERSIONS = Path(__file__).parents[1] / "alembic/versions"


def _load(name: str) -> ModuleType:
    path = next(VERSIONS.glob(f"{name}_*.py"))
    spec = importlib.util.spec_from_file_location(f"migration_{name}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ukraine_digest_migration_round_trip() -> None:
    module = _load("0057")
    assert module.revision == "0057" and module.down_revision == "0055"
    engine = create_engine("sqlite://")
    try:
        with engine.begin() as connection:
            operations = Operations(MigrationContext.configure(connection))
            module.op = operations
            module.upgrade()
            inspector = inspect(connection)
            assert "ukraine_digests" in inspector.get_table_names()
            columns = {column["name"] for column in inspector.get_columns("ukraine_digests")}
            assert columns == {
                "id",
                "period_start",
                "period_end",
                "generated_at",
                "model",
                "payload",
                "citations",
                "source_ids",
                "evidence_items",
                "prompt_tokens",
                "completion_tokens",
            }
            assert any(
                index["name"] == "ix_ukraine_digests_generated_at"
                for index in inspector.get_indexes("ukraine_digests")
            )
            connection.execute(
                sa.text(
                    "INSERT INTO ukraine_digests (period_start, period_end, generated_at, model,"
                    " payload, citations, source_ids, evidence_items) VALUES"
                    " ('2026-08-18', '2026-09-01', '2026-09-01 12:00:00', 'fixture',"
                    " '{}', '[]', '[]', 8)"
                )
            )
            module.downgrade()
            assert "ukraine_digests" not in inspect(connection).get_table_names()
    finally:
        engine.dispose()
