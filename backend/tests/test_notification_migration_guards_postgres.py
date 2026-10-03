"""Real transactional refusal paths preserve the integrated migration schema and data."""

import pytest
import sqlalchemy as sa

from notification_migration_helpers import (
    migration_database as migration_database,  # noqa: PLC0414
)
from notification_migration_helpers import (
    revision,
    seed_legacy,
    snapshot,
    table,
)
from notification_schema_inventory import owned_schema_state


def retained_state(connection):
    names = sa.inspect(connection).get_table_names()
    return owned_schema_state(connection), snapshot(connection, names)


async def refuses_unchanged(database, target, message, *, downgrade):
    before = await database.run(retained_state)
    with pytest.raises(RuntimeError, match=message):
        await database.migrate(target, downgrade=downgrade)
    assert await database.run(retained_state) == before


def corrupt_checkpoint(connection, job_id):
    jobs = table(connection, "report_jobs")
    connection.execute(jobs.update().where(jobs.c.id == job_id).values(payload_sha256="0" * 64))


async def test_corrupt_legacy_checkpoint_refuses_without_partial_postgres_ddl(migration_database):
    await migration_database.migrate("0066")
    original = await migration_database.run(seed_legacy)
    await migration_database.migrate("0082")
    await migration_database.run(corrupt_checkpoint, original["job"])
    await refuses_unchanged(
        migration_database, "head", "Repair the reported checkpoint", downgrade=False
    )
    assert await migration_database.run(revision) == "0082"


def set_frozen_ratio(connection, original, values, deleted):
    rules, alerts = table(connection, "indicators"), table(connection, "alerts")
    # A rule may be edited back to absolute mode or removed while its alerts remain.
    if deleted:
        connection.execute(rules.delete().where(rules.c.id == original["rule"]))
    else:
        connection.execute(
            rules.update().where(rules.c.id == original["rule"]).values(baseline_ratio=None)
        )
    connection.execute(alerts.update().where(alerts.c.id == original["alert"]).values(**values))


@pytest.mark.parametrize("deleted", [False, True], ids=["edited-rule", "deleted-rule"])
async def test_frozen_alert_baselines_refuse_downgrade_after_rule_changes(
    migration_database, deleted
):
    await migration_database.migrate("0066")
    original = await migration_database.run(seed_legacy)
    await migration_database.migrate("0085")
    for values in (
        {"baseline_mean": 2.0, "baseline_ratio": None},
        {"baseline_mean": None, "baseline_ratio": 3.0},
        {"baseline_mean": 2.0, "baseline_ratio": 3.0},
    ):
        await migration_database.run(set_frozen_ratio, original, values, deleted)
        await refuses_unchanged(migration_database, "0084", "baseline", downgrade=True)
        assert await migration_database.run(revision) == "0085"


def change_feedback(connection, retained):
    alerts = table(connection, "alerts")
    connection.execute(
        alerts.update().values(disposition_note="Retained analyst note" if retained else None)
    )


async def test_feedback_and_privacy_barriers_preserve_schema_and_retained_rows(migration_database):
    await migration_database.migrate("0066")
    await migration_database.run(seed_legacy)
    await migration_database.migrate("0084")
    await migration_database.run(change_feedback, True)
    await refuses_unchanged(migration_database, "0083", "retained alert feedback", downgrade=True)
    await migration_database.run(change_feedback, False)
    await migration_database.migrate("0082", downgrade=True)
    await refuses_unchanged(migration_database, "0066", "preserve privacy", downgrade=True)
