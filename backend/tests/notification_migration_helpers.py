"""Private PostgreSQL databases and legacy-schema fixtures for the combined rehearsal."""

import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from sqlalchemy.ext.asyncio import create_async_engine

from ase.application.feeds.cooperative_work import joined_thread_call
from ase.infrastructure.migrations import alembic_config

NOW = datetime(2026, 9, 1, 12, tzinfo=UTC)
NOTIFICATION_TABLES = {
    "notification_digest_preferences",
    "notification_digest_outbox",
    "private_feed_tokens",
    "notification_preferences",
    "subscription_notification_preferences",
    "alert_webhook_destinations",
    "alert_notification_routes",
    "alert_notification_outbox",
    "web_push_devices",
    "web_push_outbox",
}
LEGACY_TABLES = (
    "users",
    "teams",
    "team_invitations",
    "indicators",
    "alerts",
    "reports",
    "report_jobs",
    "report_embeddings",
    "schedules",
    "subscription_revisions",
    "subscription_editions",
    "subscription_edition_attempts",
    "subscription_delivery_outbox",
)


@dataclass(frozen=True)
class MigrationDatabase:
    url: str = field(repr=False)

    async def migrate(self, revision, *, downgrade=False):
        operation = command.downgrade if downgrade else command.upgrade
        # Fixture teardown must wait for Alembic to release its connection even
        # when the requesting test is cancelled repeatedly.
        await joined_thread_call(lambda: operation(alembic_config(self.url), revision))

    async def run(self, action, *args):
        engine = create_async_engine(self.url)
        try:
            async with engine.begin() as connection:
                return await connection.run_sync(action, *args)
        finally:
            await engine.dispose()


@pytest.fixture
async def migration_database():
    """Only the generated database is touched; no application schema fixture is used."""
    source = os.environ.get("ASE_NOTIFICATION_MIGRATION_POSTGRES_URL")
    if not source:
        pytest.skip("Set ASE_NOTIFICATION_MIGRATION_POSTGRES_URL to a disposable loopback server")
    url = sa.make_url(source)
    assert url.drivername == "postgresql+asyncpg"
    assert url.host in {"127.0.0.1", "localhost", "::1"}
    name = f"ase_notification_migration_{uuid4().hex}"
    admin = create_async_engine(url, isolation_level="AUTOCOMMIT")
    try:
        async with admin.connect() as connection:
            await connection.execute(sa.text(f'CREATE DATABASE "{name}"'))
        try:
            yield MigrationDatabase(url.set(database=name).render_as_string(hide_password=False))
        finally:
            async with admin.connect() as connection:
                await connection.execute(sa.text(f'DROP DATABASE "{name}"'))
    finally:
        await admin.dispose()


def table(connection, name):
    # Explicit target DML needs its columns, not recursive copies of related tables.
    # Independent schema snapshots still inspect every foreign-key constraint.
    return sa.Table(name, sa.MetaData(), autoload_with=connection, resolve_fks=False)


def insert_row(connection, table_name, **values):
    """Use reflected historical columns, never defaults from the current ORM."""
    target = table(connection, table_name)
    row = {}
    for column in target.c:
        if column.name in values or column.nullable or column.server_default is not None:
            continue
        if isinstance(column.type, sa.Uuid):
            row[column.name] = uuid4()
        elif isinstance(column.type, sa.Boolean):
            row[column.name] = True
        elif isinstance(column.type, sa.Integer):
            row[column.name] = 1
        elif isinstance(column.type, sa.Float):
            row[column.name] = 1.0
        elif isinstance(column.type, sa.DateTime):
            row[column.name] = NOW
        elif isinstance(column.type, sa.JSON):
            row[column.name] = []
        else:
            row[column.name] = "fixture"
    row.update(values)
    connection.execute(target.insert().values(**row))
    return row.get("id")


def snapshot_targets(connection, names):
    if not names:
        return
    available = set(sa.inspect(connection).get_table_names())
    if len(set(names)) != len(names) or any(name not in available for name in names):
        # Keep error/callback order and individual support for views or temporary tables.
        for name in names:
            yield name, table(connection, name)
        return
    metadata = sa.MetaData()
    metadata.reflect(bind=connection, only=names, resolve_fks=False)
    for name in names:
        if name not in metadata.tables:
            # Batch reflection warns and skips unreflectable tables. Recover the
            # individual error, but never accept a silently incomplete snapshot.
            table(connection, name)
            raise sa.exc.UnreflectableTableError(f"Batch reflection omitted {name!r}")
        yield name, metadata.tables[name]


def snapshot(connection, names=LEGACY_TABLES):
    result = {}
    for name, target in snapshot_targets(connection, tuple(names)):
        query = sa.select(target).order_by(*target.primary_key.columns)
        result[name] = [dict(row) for row in connection.execute(query).mappings()]
    return result


def assert_preserved(connection, previous):
    current = snapshot(connection, previous)
    for name, rows in previous.items():
        assert len(current[name]) == len(rows), name
        for before, after in zip(rows, current[name], strict=True):
            assert {key: after[key] for key in before} == before, name


def schema_state(connection):
    inspector = sa.inspect(connection)
    return {
        name: {
            "columns": [
                (column["name"], str(column["type"]), column["nullable"], column["default"])
                for column in inspector.get_columns(name)
            ],
            "indexes": inspector.get_indexes(name),
            "primary_key": inspector.get_pk_constraint(name),
            "foreign_keys": inspector.get_foreign_keys(name),
            "checks": inspector.get_check_constraints(name),
            "unique": inspector.get_unique_constraints(name),
        }
        for name in inspector.get_table_names()
    }


def revision(connection):
    return connection.scalar(sa.text("SELECT version_num FROM alembic_version"))


def seed_legacy(connection):
    owner = insert_row(connection, "users", email="owner@example.test", role="user")
    recipient = insert_row(connection, "users", email="recipient@example.test", role="user")
    team = insert_row(connection, "teams", created_by=owner, name="Migration desk")
    for status in ("pending", "accepted", "declined", "withdrawn", "expired"):
        insert_row(
            connection,
            "team_invitations",
            team_id=team,
            recipient_id=recipient,
            inviter_id=owner,
            role="member",
            status=status,
            note="Legacy note",
            expires_at=NOW + timedelta(days=7),
            responded_at=None if status == "pending" else NOW,
        )
    rule = insert_row(connection, "indicators", created_by=owner)
    alert = insert_row(
        connection,
        "alerts",
        indicator_id=rule,
        created_by=owner,
        acknowledged_at=NOW,
        acknowledged_by=owner,
        event_ids=["frozen-evidence"],
    )
    for vector in ([1.0, 0.0], [0.0, 0.0]):
        report = insert_row(connection, "reports", created_by=owner, status="ready", scope={})
        insert_row(connection, "report_embeddings", report_id=report, vector=vector)
    payload = json.dumps(
        {
            "schema_version": 1,
            "summary": {"completed_sections": 3},
            "calls": [
                {
                    "status": "in_flight",
                    "reserved_output": 100,
                    "dispatched_at": "2026-09-01T12:00:00+00:00",
                },
                {
                    "status": "completed",
                    "reserved_output": 100,
                    "completion_tokens": 50,
                    "dispatched_at": "2026-08-31T23:00:00+00:00",
                },
            ],
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    job = insert_row(
        connection,
        "report_jobs",
        owner_id=owner,
        status="queued",
        stage="queued",
        payload=payload,
        payload_bytes=len(payload.encode()),
        payload_sha256=hashlib.sha256(payload.encode()).hexdigest(),
    )
    schedule = insert_row(connection, "schedules", created_by=owner, cadence="daily")
    insert_row(
        connection,
        "subscription_revisions",
        subscription_id=schedule,
        owner_id=owner,
        revision=1,
        request_snapshot="{}",
    )
    edition = insert_row(
        connection,
        "subscription_editions",
        subscription_id=schedule,
        trigger="scheduled",
        due_at_utc=NOW,
        frozen_revision=1,
        requested_start=NOW - timedelta(days=1),
        requested_end=NOW,
        workflow="completed",
        report_quality="absent",
        coverage="unknown",
        job_id=job,
    )
    insert_row(connection, "subscription_edition_attempts", edition_id=edition, job_id=job)
    for state in ("pending", "sent", "uncertain"):
        insert_row(
            connection,
            "subscription_delivery_outbox",
            edition_id=edition,
            channel="in_app",
            event_kind="edition_available",
            state=state,
        )
    return {
        "owner": owner,
        "recipient": recipient,
        "team": team,
        "rule": rule,
        "alert": alert,
        "job": job,
        "schedule": schedule,
        "edition": edition,
        "before": snapshot(connection),
    }
