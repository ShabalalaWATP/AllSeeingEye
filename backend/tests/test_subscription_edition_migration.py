"""Additive 0035 migration against disposable populated databases only."""

import asyncio
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from alembic import command

from ase.adapters.persistence.report_job_codec import payload_columns
from ase.domain.subscription_snapshots import canonical_snapshot
from ase.infrastructure.migrations import alembic_config
from test_scope_migration import _insert

NOW = datetime(2026, 9, 14, 12, tzinfo=UTC)


def _migrate(step, config, revision: str) -> None:
    """Run an Alembic step, then restore a current loop for asyncpg's sync fallback."""
    try:
        step(config, revision)
    finally:
        asyncio.set_event_loop(asyncio.new_event_loop())


def _seed(url: str):
    # No pooling: each checkout connects on the current loop (see _migrate).
    engine = sa.create_engine(url, poolclass=sa.pool.NullPool)
    metadata = sa.MetaData()
    metadata.reflect(engine)
    with engine.begin() as connection:
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
                **payload_columns(payload),
            }
            connection.execute(metadata.tables["report_jobs"].insert().values(**values))
            original_jobs.append(values)
    return engine, schedule, owner, report, options, original_jobs


def _exercise(url: str, async_url: str) -> None:
    config = alembic_config(async_url)
    asyncio.set_event_loop(asyncio.new_event_loop())
    _migrate(command.upgrade, config, "0034")
    engine, schedule_id, owner, report_id, options, jobs = _seed(url)
    try:
        _migrate(command.upgrade, config, "0035")
        metadata = sa.MetaData()
        metadata.reflect(engine)
        indexes = {row["name"] for row in sa.inspect(engine).get_indexes("subscription_editions")}
        assert {
            "ix_subscription_edition_active",
            "ix_subscription_edition_due_status",
            "ix_subscription_edition_history",
        } <= indexes
        with engine.connect() as connection:
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
                    sa.select(sa.func.count()).select_from(
                        metadata.tables["subscription_revisions"]
                    )
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
        with engine.begin() as connection:
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
        with pytest.raises(RuntimeError, match="retained subscription edition records"):
            _migrate(command.downgrade, config, "0034")
        with engine.begin() as connection:
            connection.execute(metadata.tables["subscription_revisions"].delete())
        _migrate(command.downgrade, config, "0034")
        assert "subscription_editions" not in sa.inspect(engine).get_table_names()
    finally:
        engine.dispose()


def test_sqlite_legacy_upgrade_keeps_due_slots_jobs_and_unknown_coverage(tmp_path: Path) -> None:
    database = tmp_path / "s01-disposable.db"
    _exercise(f"sqlite:///{database}", f"sqlite+aiosqlite:///{database}")


# asyncpg is the only shipped PostgreSQL driver; its sync fallback is deprecated upstream.
@pytest.mark.filterwarnings("ignore:The async_fallback dialect argument:DeprecationWarning")
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
    # The project ships asyncpg only; its dialect's synchronous fallback drives the
    # blocking seed and inspection helpers without adding a second driver.
    sync_url = parsed.update_query_dict({"async_fallback": "true"})
    _exercise(sync_url.render_as_string(hide_password=False), async_url)
