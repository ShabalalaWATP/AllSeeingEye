"""Real combined PostgreSQL upgrades and explicit feature rollback, without senders."""

from datetime import timedelta
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from ase.adapters.persistence.base import Base
from notification_migration_helpers import (
    NOTIFICATION_TABLES,
    NOW,
    assert_preserved,
    insert_row,
    revision,
    schema_state,
    seed_legacy,
    table,
)
from notification_migration_helpers import (
    migration_database as migration_database,  # noqa: PLC0414
)
from owned_postgres import owned_migration_test


def assert_head(connection):
    assert revision(connection) == "0089"
    changed = NOTIFICATION_TABLES | {
        "team_invitation_receipts",
        "report_job_monthly_usage",
        "report_jobs",
        "report_embeddings",
        "alerts",
        "indicators",
        "forecast_review_reminders",
        "subscription_delivery_outbox",
        "subscription_edition_attempts",
        "activity_samples",
        "llm_usage",
    }
    context = MigrationContext.configure(
        connection,
        opts={
            "include_object": lambda _obj, name, kind, _reflected, _comparison: (
                kind != "table" or name in changed
            ),
        },
    )
    assert compare_metadata(context, Base.metadata) == []
    assert set(sa.inspect(connection).get_table_names()) >= NOTIFICATION_TABLES


def assert_unenrolled(connection):
    for name in NOTIFICATION_TABLES:
        assert (
            connection.scalar(sa.select(sa.func.count()).select_from(table(connection, name))) == 0
        )


@owned_migration_test
async def test_empty_combined_upgrade_roundtrip_and_model_parity(migration_database):
    await migration_database.migrate("0082")
    before = await migration_database.run(schema_state)
    await migration_database.migrate("head")
    await migration_database.run(assert_head)
    await migration_database.run(assert_unenrolled)
    await migration_database.migrate("0082", downgrade=True)
    assert await migration_database.run(schema_state) == before
    assert await migration_database.run(revision) == "0082"
    await migration_database.migrate("head")
    await migration_database.run(assert_head)


def assert_backfills(connection, original):
    assert_preserved(connection, original["before"])
    receipt = (
        connection.execute(sa.select(table(connection, "team_invitation_receipts")))
        .mappings()
        .one()
    )
    assert receipt["status"] == "accepted" and receipt["recipient_id"] == original["recipient"]
    assert receipt["recipient_username"] is receipt["recipient_display_name"] is None
    jobs = table(connection, "report_jobs")
    assert connection.scalar(sa.select(jobs.c.summary)) == {
        "completed_sections": 3,
        "origin": "research",
    }
    usage = table(connection, "report_job_monthly_usage")
    projected = connection.execute(
        sa.select(
            usage.c.owner_requests,
            usage.c.owner_output_tokens,
            usage.c.subscription_requests,
            usage.c.subscription_output_tokens,
        ).order_by(usage.c.month)
    ).all()
    assert projected == [(0, 0, 1, 50), (1, 100, 1, 100)]
    embeddings = table(connection, "report_embeddings")
    for row in connection.execute(sa.select(embeddings)).mappings():
        assert row["vector_valid"] == (row["vector"] == [1.0, 0.0])
    deliveries = table(connection, "subscription_delivery_outbox")
    for row in connection.execute(sa.select(deliveries)).mappings():
        assert row["lease_token"] is row["next_attempt_at"] is row["safe_reason"] is None
    rules = table(connection, "indicators")
    assert connection.execute(sa.select(rules.c.baseline_ratio, rules.c.baseline_days)).one() == (
        None,
        30,
    )


def rejects(connection, name, **values):
    with pytest.raises(sa.exc.IntegrityError), connection.begin_nested():
        insert_row(connection, name, **values)


def write_notification_state(connection, original):
    owner = original["owner"]
    insert_row(
        connection,
        "notification_preferences",
        user_id=owner,
        email_enabled=True,
        include_names=False,
    )
    insert_row(
        connection,
        "subscription_notification_preferences",
        user_id=owner,
        subscription_id=original["schedule"],
        email_policy="every_edition",
        attention=True,
    )
    insert_row(
        connection,
        "private_feed_tokens",
        user_id=owner,
        token_hash="a" * 64,
        security_version=1,
        include_titles=False,
    )
    insert_row(
        connection,
        "notification_digest_preferences",
        user_id=owner,
        enabled=True,
        timezone="Europe/London",
        hour=8,
        cursor_at=NOW,
        next_due_at=NOW + timedelta(days=1),
    )
    rejects(
        connection,
        "notification_digest_preferences",
        user_id=original["recipient"],
        enabled=True,
        timezone="UTC",
        hour=24,
        cursor_at=NOW,
        next_due_at=NOW,
    )
    digest = {
        "user_id": owner,
        "local_day": "2026-09-01",
        "timezone": "Europe/London",
        "window_start": NOW - timedelta(days=1),
        "window_end": NOW,
        "state": "uncertain",
        "attempts": 1,
        "lease_token": uuid4(),
    }
    insert_row(connection, "notification_digest_outbox", **digest)
    rejects(connection, "notification_digest_outbox", **digest)
    rejects(
        connection,
        "notification_digest_outbox",
        **(digest | {"local_day": "2026-09-02", "attempts": 4}),
    )
    rejects(
        connection,
        "notification_digest_outbox",
        **(digest | {"local_day": "2026-09-02", "window_start": NOW}),
    )
    webhook = insert_row(
        connection,
        "alert_webhook_destinations",
        created_by=owner,
        url_encrypted="synthetic-opaque-ciphertext",
        enabled=True,
    )
    insert_row(
        connection,
        "alert_notification_routes",
        indicator_id=original["rule"],
        configured_by=owner,
        email_enabled=True,
        webhook_id=webhook,
        revision=1,
    )
    route = {
        "alert_id": original["alert"],
        "channel": "webhook",
        "destination_ref": str(webhook),
        "route_revision": 1,
        "state": "uncertain",
        "attempts": 1,
    }
    insert_row(connection, "alert_notification_outbox", **route)
    rejects(connection, "alert_notification_outbox", **route)
    device = {
        "user_id": owner,
        "family_id": uuid4(),
        "security_version": 1,
        "endpoint_hash": "b" * 64,
        "encrypted_subscription": "synthetic-opaque-push-subscription",
        "next_check_at": NOW,
    }
    device_id = insert_row(connection, "web_push_devices", **device)
    rejects(connection, "web_push_devices", **device)
    delivery = {"device_id": device_id, "alert_id": original["alert"], "state": "uncertain"}
    insert_row(connection, "web_push_outbox", **delivery)
    rejects(connection, "web_push_outbox", **delivery)
    rejects(connection, "web_push_outbox", **(delivery | {"device_id": uuid4()}))
    devices = table(connection, "web_push_devices")
    connection.execute(devices.delete().where(devices.c.id == device_id))
    assert (
        connection.scalar(
            sa.select(sa.func.count()).select_from(table(connection, "web_push_outbox"))
        )
        == 0
    )
    # Retain a device and delivery so the rollback also checks the correct FK drop order.
    device_id = insert_row(connection, "web_push_devices", **device)
    insert_row(connection, "web_push_outbox", **(delivery | {"device_id": device_id}))


@owned_migration_test
async def test_legacy_upgrade_constraints_and_explicit_notification_rollback(migration_database):
    await migration_database.migrate("0066")
    original = await migration_database.run(seed_legacy)
    await migration_database.migrate("head")
    await migration_database.run(assert_head)
    await migration_database.run(assert_unenrolled)
    await migration_database.run(assert_backfills, original)
    await migration_database.run(write_notification_state, original)
    # Downgrade intentionally discards new opt-ins/outboxes; legacy records must survive.
    for target, removed in (
        ("0088", {"web_push_devices", "web_push_outbox"}),
        (
            "0087",
            {
                "alert_webhook_destinations",
                "alert_notification_routes",
                "alert_notification_outbox",
            },
        ),
        ("0086", {"notification_preferences", "notification_digest_outbox", "private_feed_tokens"}),
    ):
        await migration_database.migrate(target, downgrade=True)
        current_schema = await migration_database.run(schema_state)
        assert not removed & current_schema.keys()
        assert await migration_database.run(revision) == target
        await migration_database.run(assert_preserved, original["before"])
    await migration_database.migrate("0082", downgrade=True)
    await migration_database.run(assert_preserved, original["before"])
    await migration_database.migrate("head")
    await migration_database.run(assert_head)
    await migration_database.run(assert_unenrolled)
    await migration_database.run(assert_backfills, original)
