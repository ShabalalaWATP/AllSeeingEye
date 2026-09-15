"""AI allowance migration creates the policy, counter and reservation tables safely."""

from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError

from ase.adapters.persistence.ai_usage_models import AiUsagePolicyRow
from ase.adapters.persistence.base import Base


def _migration():
    path = Path(__file__).parents[1] / "alembic/versions/0045_ai_usage_allowances.py"
    spec = importlib.util.spec_from_file_location("ai_usage_migration", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ai_usage_migration_and_retained_data_guard():
    module = _migration()
    assert module.revision == "0045" and module.down_revision == "0044"
    engine = create_engine("sqlite://")
    try:
        with engine.begin() as connection:
            module.op = Operations(MigrationContext.configure(connection))
            module.upgrade()
            names = set(inspect(connection).get_table_names())
            assert {
                "ai_usage_policies",
                "ai_usage_policy_overrides",
                "ai_usage_counters",
                "ai_usage_reservations",
                "ai_usage_totals",
            } <= names
            columns = {
                column["name"]
                for column in inspect(connection).get_columns("ai_usage_reservations")
            }
            assert {"call_id", "team_id", "system", "dispatched_at"} <= columns
            now = datetime.now(UTC)
            connection.execute(
                AiUsagePolicyRow.__table__.insert().values(
                    id=uuid4(),
                    scope="system",
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
                "ai_usage_policy_overrides",
                "ai_usage_counters",
                "ai_usage_reservations",
                "ai_usage_totals",
            } & set(inspect(connection).get_table_names())
    finally:
        engine.dispose()


def _load(name: str, filename: str):
    path = Path(__file__).parents[1] / "alembic/versions" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_site_and_system_policies_are_each_unique_when_enabled():
    tables = _migration()
    uniqueness = _load("ai_usage_uniqueness", "0051_ai_usage_policy_uniqueness.py")
    engine = create_engine("sqlite://")
    try:
        with engine.begin() as connection:
            operations = Operations(MigrationContext.configure(connection))
            tables.op = uniqueness.op = operations
            tables.upgrade()
            uniqueness.upgrade()
            now = datetime.now(UTC)

            def insert(scope: str, enabled: bool = True) -> None:
                connection.execute(
                    AiUsagePolicyRow.__table__.insert().values(
                        id=uuid4(),
                        scope=scope,
                        target_id=None,
                        period="day",
                        request_limit=None,
                        token_limit=None,
                        enabled=enabled,
                        revision=1,
                        created_at=now,
                        updated_at=now,
                    )
                )

            insert("global")
            insert("system")
            insert("system", enabled=False)
            with pytest.raises(IntegrityError), connection.begin_nested():
                insert("system")
    finally:
        engine.dispose()


def test_ai_usage_migrations_match_the_models():
    tables = _migration()
    uniqueness = _load("ai_usage_parity", "0051_ai_usage_policy_uniqueness.py")
    names = {
        "ai_usage_policies",
        "ai_usage_policy_overrides",
        "ai_usage_counters",
        "ai_usage_reservations",
        "ai_usage_totals",
    }
    engine = create_engine("sqlite://")
    try:
        with engine.begin() as connection:
            tables.op = uniqueness.op = Operations(MigrationContext.configure(connection))
            tables.upgrade()
            uniqueness.upgrade()
            context = MigrationContext.configure(
                connection,
                opts={
                    "include_object": lambda obj, name, kind, reflected, compare: (
                        (kind != "table" or name in names)
                        and (
                            kind == "table"
                            or getattr(obj, "table", None) is None
                            or obj.table.name in names
                        )
                    )
                },
            )
            assert compare_metadata(context, Base.metadata) == []
    finally:
        engine.dispose()
