"""Migration 0057 creates the small explainer cache table and drops it cleanly."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect


def _migration():
    path = Path(__file__).parents[1] / "alembic/versions/0057_economy_explainer_cache.py"
    spec = importlib.util.spec_from_file_location("economy_explainer_migration", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_economy_explainer_cache_table_is_created_and_reversible():
    module = _migration()
    assert module.revision == "0057" and module.down_revision == "0056"
    engine = create_engine("sqlite://")
    try:
        with engine.begin() as connection:
            module.op = Operations(MigrationContext.configure(connection))
            module.upgrade()
            inspector = inspect(connection)
            assert "economy_explainers" in inspector.get_table_names()
            columns = {column["name"] for column in inspector.get_columns("economy_explainers")}
            assert columns == {
                "id",
                "fingerprint",
                "window_start",
                "payload",
                "model",
                "generated_at",
                "snapshot_fetched_at",
                "prompt_tokens",
                "completion_tokens",
            }
            indexes = {index["name"] for index in inspector.get_indexes("economy_explainers")}
            assert indexes == {
                "ix_economy_explainers_fingerprint",
                "ix_economy_explainers_generated_at",
            }
            module.downgrade()
            assert "economy_explainers" not in inspect(connection).get_table_names()
    finally:
        engine.dispose()
