"""Additive 0035 migration against disposable populated databases only."""

import asyncio
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from sqlalchemy.ext.asyncio import create_async_engine

from ase.adapters.persistence.report_job_codec import payload_columns
from ase.domain.subscription_snapshots import canonical_snapshot
from ase.infrastructure.migrations import alembic_config
from test_scope_migration import _insert

NOW = datetime(2026, 9, 14, 12, tzinfo=UTC)


async def _run(url: str, action, *args):
    """Run existing synchronous inspections through the supported async bridge."""
    engine = create_async_engine(url, poolclass=sa.pool.NullPool)
    try:
        async with engine.begin() as connection:
            return await connection.run_sync(action, *args)
    finally:
        await engine.dispose()


def _seed(url: str):
    # The research-brief migration also uses this SQLite-only seed wrapper.
    engine = sa.create_engine(url, poolclass=sa.pool.NullPool)
    try:
        with engine.begin() as connection:
            values = _seed_rows(connection)
    except BaseException:
        engine.dispose()
        raise
    return engine, *values


def _seed_rows(connection: sa.Connection):
    metadata = sa.MetaData()
    metadata.reflect(connection)
    owner = _insert(connection, metadata.tables["users"], email="s01@example.com", role="user")
    report = _insert(connection, metadata.tables["reports"], created_by=owner, status="ready")
    options = {
        "baseline_report_id": report,
        "seen_content_signatures": ["prior-fingerprint"],
        "monthday": 31,
    }
    schedule = _insert(
        connection,
        metadata.tables["schedules"],
        created_by=owner,
        name="Legacy monthly",
        template_id="intsum",
        cadence="monthly",
        hour_utc=6,
        weekday=0,
        next_run_at=NOW + timedelta(days=1),
        last_run_at=NOW,
        last_report_id=report,
        research_options=options,
    )
    original_jobs = []
    for status in ("queued", "paused", "failed"):
        payload = {
            "schema_version": 1,
            "summary": {},
            "request_digest": "a" * 64,
            "section_packet_digest": "b" * 64,
            "usage_reservation_hash": "c" * 64,
        }
        columns = payload_columns(payload)
        # The separate summary projection was introduced after this schema.
        columns.pop("summary")
        values = {
            "id": uuid4().hex,
            "request_key": uuid4().hex,
            "owner_id": owner,
            "team_id": None,
            "title": "Retained job",
            "status": status,
            "stage": "model_call" if status == "paused" else status,
            "created_at": NOW,
            "updated_at": NOW,
            "revision": 1,
            "lease_token": None,
            "lease_until": None,
            "report_id": uuid4().hex,
            "version_id": uuid4().hex,
            "error": "call_outcome_unknown" if status == "paused" else None,
            **columns,
        }
        connection.execute(metadata.tables["report_jobs"].insert().values(**values))
        original_jobs.append(values)
    return schedule, owner, report, options, original_jobs


def _assert_upgrade(connection: sa.Connection, retained_seed) -> None:
    schedule_id, owner, report_id, options, jobs = retained_seed
    metadata = sa.MetaData()
    metadata.reflect(connection)
    indexes = {row["name"] for row in sa.inspect(connection).get_indexes("subscription_editions")}
    assert {
        "ix_subscription_edition_active",
        "ix_subscription_edition_due_status",
        "ix_subscription_edition_history",
    } <= indexes
    schedule = (
        connection.execute(
            sa.select(metadata.tables["schedules"]).where(
                metadata.tables["schedules"].c.id == schedule_id
            )
        )
        .mappings()
        .one()
    )
    assert schedule["name"] == "Legacy monthly"
    # SQLite returns the stored hex text; PostgreSQL returns a UUID.
    assert UUID(str(schedule["last_report_id"])) == UUID(report_id)
    assert schedule["next_run_at"] is not None
    assert schedule["research_options"] == {**options, "last_coverage": "unknown"}
    assert (
        connection.scalar(
            sa.select(sa.func.count()).select_from(metadata.tables["subscription_editions"])
        )
        == 0
    )
    assert (
        connection.scalar(
            sa.select(sa.func.count()).select_from(metadata.tables["subscription_revisions"])
        )
        == 0
    )
    retained = (
        connection.execute(
            sa.select(metadata.tables["report_jobs"]).order_by(
                metadata.tables["report_jobs"].c.status
            )
        )
        .mappings()
        .all()
    )
    assert len(retained) == 3
    before = {UUID(str(row["id"])): row for row in jobs}
    for row in retained:
        old = before[UUID(str(row["id"]))]
        for key in ("status", "payload", "payload_sha256", "payload_bytes", "error"):
            assert row[key] == old[key]
    snapshot = canonical_snapshot(
        {
            "schema_version": 1,
            "template_id": "intsum",
            "scope": {},
            "request": {},
            "recurrence": {},
            "collection_policy": "rolling_snapshot_v1",
            "avoid_repetition": True,
        }
    )
    connection.execute(
        metadata.tables["subscription_revisions"]
        .insert()
        .values(
            subscription_id=schedule_id,
            revision=1,
            owner_id=owner,
            team_id=None,
            request_snapshot=snapshot,
            compatibility_fingerprint="a" * 64,
            recurrence_policy="legacy_utc_v1",
            collection_policy="rolling_snapshot_v1",
            enabled=True,
            created_at=NOW,
            brief_revision_id=None,
        )
    )


def _clear_revision(connection: sa.Connection) -> None:
    revisions = sa.Table("subscription_revisions", sa.MetaData(), autoload_with=connection)
    connection.execute(revisions.delete())


def _assert_downgrade(connection: sa.Connection) -> None:
    assert "subscription_editions" not in sa.inspect(connection).get_table_names()


def _exercise(async_url: str) -> None:
    # Alembic owns its loop. Each inspection owns and disposes its separate engine
    # before the next revision changes the physical database schema.
    config = alembic_config(async_url)
    command.upgrade(config, "0034")
    retained_seed = asyncio.run(_run(async_url, _seed_rows))
    command.upgrade(config, "0035")
    asyncio.run(_run(async_url, _assert_upgrade, retained_seed))
    with pytest.raises(RuntimeError, match="retained subscription edition records"):
        command.downgrade(config, "0034")
    asyncio.run(_run(async_url, _clear_revision))
    command.downgrade(config, "0034")
    asyncio.run(_run(async_url, _assert_downgrade))


def test_sqlite_legacy_upgrade_keeps_due_slots_jobs_and_unknown_coverage(tmp_path: Path) -> None:
    database = tmp_path / "s01-disposable.db"
    _exercise(f"sqlite+aiosqlite:///{database}")


@pytest.mark.postgres
def test_postgres_disposable_upgrade_when_explicitly_configured() -> None:
    async_url = os.environ.get("ASE_TEST_MIGRATION_POSTGRES_URL")
    if not async_url:
        pytest.skip("No explicit disposable PostgreSQL migration database configured.")
    parsed = sa.engine.make_url(async_url)
    if not (
        parsed.drivername.startswith("postgresql+")
        and (parsed.database or "").startswith("ase_s01_disposable_")
    ):
        pytest.fail("The PostgreSQL migration URL must name an ase_s01_disposable_ database.")
    _exercise(async_url)
