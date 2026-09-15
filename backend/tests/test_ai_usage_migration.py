"""AI allowance migration creates the policy, counter and reservation tables safely."""

from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect

from ase.adapters.persistence.ai_usage_models import AiUsagePolicyRow


def _migration():
    path = Path(__file__).parents[1] / "alembic/versions/0035_ai_usage_allowances.py"
    spec = importlib.util.spec_from_file_location("ai_usage_migration", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ai_usage_migration_and_retained_data_guard():
    module = _migration()
    assert module.revision == "0035" and module.down_revision == "0034"
    engine = create_engine("sqlite://")
    try:
        with engine.begin() as connection:
            module.op = Operations(MigrationContext.configure(connection))
            module.upgrade()
            names = set(inspect(connection).get_table_names())
            assert {
                "ai_usage_policies",
                "ai_usage_counters",
                "ai_usage_reservations",
            } <= names
            now = datetime.now(UTC)
            connection.execute(
                AiUsagePolicyRow.__table__.insert().values(
                    id=uuid4(),
                    scope="global",
                    target_id=None,
                    period="month",
                    request_limit=0,
                    token_limit=0,
                    enabled=True,
                    revision=1,
                    created_at=now,
                    updated_at=now,
                )
            )
            with pytest.raises(RuntimeError, match="AI usage records remain"):
                module.downgrade()
            connection.execute(AiUsagePolicyRow.__table__.delete())
            module.downgrade()
            assert not {
                "ai_usage_policies",
                "ai_usage_counters",
                "ai_usage_reservations",
            } & set(inspect(connection).get_table_names())
    finally:
        engine.dispose()
