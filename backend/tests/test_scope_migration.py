"""Legacy personal ownership and frozen evidence survive the scope migration."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import sqlalchemy as sa
from alembic import command
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from ase.adapters.persistence.audit import SqlAuditLogRepository
from ase.domain.audit import AuditAction
from ase.infrastructure.migrations import alembic_config


async def _assert_audit_readable(database_url: str) -> None:
    engine = create_async_engine(database_url)
    try:
        async with async_sessionmaker(engine)() as session:
            entries = await SqlAuditLogRepository(session).list_before(None, 100)
            assert len(entries) == 5
            assert all(entry.action is AuditAction.LEGACY_SCOPE_CONFLICT for entry in entries)
    finally:
        await engine.dispose()


def _insert(connection: sa.Connection, table: sa.Table, **values: Any) -> str:
    """Populate required legacy columns; no application defaults from the new ORM are used."""
    row: dict[str, Any] = {"id": uuid4().hex}
    for column in table.columns:
        if column.name in row or column.nullable:
            continue
        if isinstance(column.type, sa.JSON):
            row[column.name] = {}
        elif isinstance(column.type, sa.DateTime):
            row[column.name] = datetime(2026, 9, 6, tzinfo=UTC)
        elif isinstance(column.type, sa.Boolean):
            row[column.name] = True
        elif isinstance(column.type, sa.Integer):
            row[column.name] = 1
        elif isinstance(column.type, sa.Float):
            row[column.name] = 0.0
        else:
            row[column.name] = "fixture"
    row.update(values)
    connection.execute(table.insert().values(**row))
    return str(row["id"])


def test_scope_upgrade_preserves_records_and_inventories_legacy_conflicts(tmp_path: Path) -> None:
    database = tmp_path / "scope-migration.db"
    config = alembic_config(f"sqlite+aiosqlite:///{database}")
    command.upgrade(config, "0013")
    engine = sa.create_engine(f"sqlite:///{database}")
    metadata = sa.MetaData()
    metadata.reflect(engine)
    with engine.begin() as connection:
        owner = _insert(connection, metadata.tables["users"], email="one@example.com", role="user")
        other = _insert(connection, metadata.tables["users"], email="two@example.com", role="user")
        aoi = _insert(connection, metadata.tables["aois"], created_by=owner)
        plan = _insert(
            connection, metadata.tables["collection_plans"], created_by=other, aoi_id=aoi
        )
        indicator = _insert(
            connection, metadata.tables["indicators"], created_by=owner, plan_id=plan
        )
        report = _insert(
            connection, metadata.tables["reports"], created_by=owner, scope={"plan": plan}
        )
        version = _insert(
            connection,
            metadata.tables["report_versions"],
            report_id=report,
            evidence=[{"id": "frozen", "hash": "unaltered"}],
            body={"summary": "Historical"},
        )
        schedule = _insert(connection, metadata.tables["schedules"], created_by=owner, plan_id=plan)
        alert = _insert(
            connection, metadata.tables["alerts"], indicator_id=indicator, report_id=report
        )
        orphan = _insert(connection, metadata.tables["alerts"], indicator_id=uuid4().hex)
        original_version = dict(
            connection.execute(sa.select(metadata.tables["report_versions"])).mappings().one()
        )
    command.upgrade(config, "0014")
    upgraded = sa.MetaData()
    upgraded.reflect(engine)
    with engine.connect() as connection:
        for table_name, expected in (
            ("aois", aoi),
            ("collection_plans", plan),
            ("indicators", indicator),
            ("reports", report),
            ("schedules", schedule),
        ):
            row = connection.execute(sa.select(upgraded.tables[table_name])).mappings().one()
            assert row["id"] == expected and row["team_id"] is None
        alerts = {
            row["id"]: row
            for row in connection.execute(sa.select(upgraded.tables["alerts"])).mappings()
        }
        assert alerts[alert]["created_by"] == owner
        assert alerts[orphan]["created_by"] is None
        assert all(row["team_id"] is None for row in alerts.values())
        assert (
            dict(connection.execute(sa.select(upgraded.tables["report_versions"])).mappings().one())
            == original_version
        )
        entries = connection.execute(sa.select(upgraded.tables["audit_log"])).mappings().all()
        assert len(entries) == 5
        assert all(entry["action"] == "legacy_scope_conflict" for entry in entries)
        assert {entry["details"]["reason"] for entry in entries} == {
            "missing_target",
            "different_personal_owner",
        }
        assert all(
            set(entry["details"])
            == {"source_table", "source_id", "target_table", "target_id", "reason"}
            for entry in entries
        )
        assert sa.inspect(connection).get_foreign_keys("reports")[0]["referred_table"] == "teams"
    asyncio.run(_assert_audit_readable(f"sqlite+aiosqlite:///{database}"))
    command.downgrade(config, "0013")
    downgraded = sa.MetaData()
    downgraded.reflect(engine)
    with engine.connect() as connection:
        assert "team_id" not in downgraded.tables["reports"].c
        assert "created_by" not in downgraded.tables["alerts"].c
        assert connection.scalar(sa.select(downgraded.tables["report_versions"].c.id)) == version
        assert (
            connection.scalar(
                sa.select(sa.func.count()).select_from(downgraded.tables["audit_log"])
            )
            == 5
        )
    engine.dispose()
