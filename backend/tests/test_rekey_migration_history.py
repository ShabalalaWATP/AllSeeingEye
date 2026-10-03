"""Re-keyed Codex migrations extend real released history without rewriting its data."""

import hashlib
import json

import pytest
import sqlalchemy as sa
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory

from ase.adapters.persistence.base import Base
from ase.domain.report_jobs import MAX_JOB_SUMMARY_BYTES, canonical_job_payload
from ase.infrastructure.migrations import alembic_config
from notification_migration_helpers import (
    NOW,
    MigrationDatabase,
    assert_preserved,
    insert_row,
    revision,
    seed_legacy,
    snapshot,
    table,
)
from notification_migration_helpers import (
    migration_database as migration_database,  # noqa: PLC0414
)
from notification_schema_inventory import owned_schema_state
from test_notification_migration_postgres import assert_backfills, assert_unenrolled


@pytest.fixture(params=["sqlite", "postgres"])
def rekey_database(request, tmp_path):
    def reflect_uuid(inspector, _table, column):
        # SQLite reflects Alembic's UUID columns as CHAR(32). Restore the bind
        # type for the shared historical fixture, without consulting live models.
        if (
            inspector.bind.dialect.name == "sqlite"
            and isinstance(column["type"], sa.CHAR)
            and column["type"].length == 32
        ):
            column["type"] = sa.Uuid()

    sa.event.listen(sa.MetaData, "column_reflect", reflect_uuid)
    try:
        if request.param == "postgres":
            yield request.getfixturevalue("migration_database")
        else:
            yield MigrationDatabase(f"sqlite+aiosqlite:///{(tmp_path / 'rekey.db').as_posix()}")
    finally:
        sa.event.remove(sa.MetaData, "column_reflect", reflect_uuid)


def test_rekey_graph_keeps_released_history_and_has_one_head():
    scripts = ScriptDirectory.from_config(alembic_config("sqlite+aiosqlite://"))
    assert scripts.get_heads() == ["0089"]
    assert scripts.get_revision("0075").down_revision == "0066"
    for number in range(76, 90):
        assert scripts.get_revision(f"{number:04d}").down_revision == f"{number - 1:04d}"
    assert {item.revision for item in scripts.walk_revisions()} >= {
        "0082",
        "0083",
        "0084",
        "0085",
        "0086",
        "0087",
        "0088",
        "0089",
    }


def stable_schema(connection):
    def normalise(value):
        if isinstance(value, sa.sql.elements.TextClause):
            return str(value)
        if isinstance(value, dict):
            return {key: normalise(item) for key, item in value.items()}
        if isinstance(value, list):
            return [normalise(item) for item in value]
        return value

    return normalise(owned_schema_state(connection))


def retained_state(connection):
    return stable_schema(connection), snapshot(connection, sa.inspect(connection).get_table_names())


def seed_released_features(connection):
    original = seed_legacy(connection)
    owner, team = original["owner"], original["team"]
    reports = table(connection, "reports")
    report = connection.scalar(sa.select(reports.c.id).order_by(reports.c.id).limit(1))
    version = insert_row(connection, "report_versions", report_id=report, status="ready")
    post = insert_row(
        connection,
        "team_board_posts",
        team_id=team,
        author_id=owner,
        subject_kind="report_version",
        subject_id=report,
        subject_version=1,
    )
    insert_row(
        connection,
        "team_board_mentions",
        post_id=post,
        recipient_id=original["recipient"],
        team_id=team,
        handle="recipient",
        read_at=NOW,
    )
    insert_row(connection, "bell_preferences", user_id=owner, muted_kinds=["report"])
    insert_row(connection, "bell_rule_mutes", user_id=owner, indicator_id=original["rule"])
    rules = table(connection, "indicators")
    connection.execute(rules.update().where(rules.c.id == original["rule"]).values(resumed_at=NOW))
    insert_row(
        connection,
        "evaluation_runs",
        actor_id=owner,
        status="completed",
        active_slot=None,
        max_calls=2,
        calls_reserved=2,
        calls_failed=0,
        has_artefact=True,
        artefact=b"retained-evaluation",
        finished_at=NOW,
    )
    insert_row(
        connection,
        "citation_verdicts",
        report_id=report,
        report_version_id=version,
        owner_id=owner,
        reviewer_id=owner,
        team_id=team,
        relation="supporting",
        verdict="supports",
        note="Retained citation review",
    )
    copied_report = insert_row(
        connection, "reports", created_by=owner, team_id=team, status="ready"
    )
    insert_row(
        connection,
        "report_team_copies",
        report_id=copied_report,
        team_id=team,
        source_report_id=report,
        source_version_id=version,
        copied_by=owner,
        content_sha256="a" * 64,
    )
    original["before"] = snapshot(
        connection,
        [name for name in sa.inspect(connection).get_table_names() if name != "alembic_version"],
    )
    return original


def assert_released_schema(connection, before):
    after = stable_schema(connection)
    for name, properties in before.items():
        assert name in after
        for kind, values in properties.items():
            if isinstance(values, list):
                assert all(value in after[name][kind] for value in values), (name, kind)
            else:
                assert after[name][kind] == values, (name, kind)


async def test_fresh_rekey_upgrade_is_complete_unenrolled_and_repeatable(rekey_database):
    await rekey_database.migrate("head")
    assert await rekey_database.run(revision) == "0089"
    await rekey_database.run(assert_unenrolled)
    await rekey_database.run(assert_model_parity)
    state = await rekey_database.run(retained_state)
    assert {
        "evaluation_runs",
        "citation_verdicts",
        "report_team_copies",
        "team_board_mentions",
        "bell_preferences",
        "team_invitation_receipts",
        "forecast_review_reminders",
    } <= state[0].keys()
    await rekey_database.migrate("head")
    assert await rekey_database.run(retained_state) == state


def assert_model_parity(connection):
    context = MigrationContext.configure(connection)
    assert compare_metadata(context, Base.metadata) == []


async def test_populated_main0081_upgrade_preserves_released_features(rekey_database):
    await rekey_database.migrate("0081")
    original = await rekey_database.run(seed_released_features)
    old_schema = await rekey_database.run(stable_schema)
    await rekey_database.migrate("head")
    assert await rekey_database.run(revision) == "0089"
    await rekey_database.run(assert_released_schema, old_schema)
    await rekey_database.run(assert_backfills, original)
    await rekey_database.run(assert_unenrolled)
    await rekey_database.run(assert_model_parity)
    await rekey_database.run(assert_preserved, original["before"])


def corrupt_checkpoint(connection, job_id, value):
    jobs = table(connection, "report_jobs")
    previous = connection.scalar(sa.select(jobs.c.payload_sha256).where(jobs.c.id == job_id))
    connection.execute(jobs.update().where(jobs.c.id == job_id).values(payload_sha256=value))
    return previous


async def test_main0081_corrupt_checkpoint_upgrade_is_repairable(rekey_database):
    await rekey_database.migrate("0081")
    original = await rekey_database.run(seed_released_features)
    valid_hash = await rekey_database.run(corrupt_checkpoint, original["job"], "0" * 64)
    before = await rekey_database.run(retained_state)
    with pytest.raises(RuntimeError, match="Repair the reported checkpoint"):
        await rekey_database.migrate("head")
    # SQLite commits completed revisions individually; PostgreSQL rolls back the
    # transaction. Neither backend may leave partial performance-projection DDL.
    sqlite = sa.make_url(rekey_database.url).get_backend_name() == "sqlite"
    assert await rekey_database.run(revision) == ("0082" if sqlite else "0081")
    failed_schema = await rekey_database.run(stable_schema)
    assert "report_job_monthly_usage" not in failed_schema
    assert "summary" not in {column[0] for column in failed_schema["report_jobs"]["columns"]}
    await rekey_database.run(assert_released_schema, before[0])
    before[1].pop("alembic_version")
    await rekey_database.run(assert_preserved, before[1])
    await rekey_database.run(corrupt_checkpoint, original["job"], valid_hash)
    await rekey_database.migrate("head")
    assert await rekey_database.run(revision) == "0089"
    await rekey_database.run(assert_backfills, original)
    await rekey_database.run(assert_unenrolled)


async def test_rekeyed_privacy_barrier_keeps_main_and_receipt_state(rekey_database):
    await rekey_database.migrate("0081")
    await rekey_database.run(seed_released_features)
    await rekey_database.migrate("0082")
    before = await rekey_database.run(retained_state)
    with pytest.raises(RuntimeError, match="preserve privacy"):
        await rekey_database.migrate("0081", downgrade=True)
    assert await rekey_database.run(retained_state) == before


def seed_frozen_alert(connection, original, deleted):
    rules = table(connection, "indicators")
    if deleted:
        # The actual alert FK retains a firing after rule deletion on PostgreSQL.
        connection.execute(rules.delete().where(rules.c.id == original["rule"]))
    alerts = table(connection, "alerts")
    connection.execute(
        alerts.update()
        .where(alerts.c.id == original["alert"])
        .values(baseline_mean=2.0, baseline_ratio=3.0),
    )


@pytest.mark.parametrize("deleted", [False, True], ids=["absolute-rule", "deleted-rule"])
async def test_rekeyed_frozen_ratio_barrier_preserves_main_features(rekey_database, deleted):
    await rekey_database.migrate("0081")
    original = await rekey_database.run(seed_released_features)
    await rekey_database.migrate("0085")
    await rekey_database.run(seed_frozen_alert, original, deleted)
    before = await rekey_database.run(retained_state)
    with pytest.raises(RuntimeError, match="retained alert baseline"):
        await rekey_database.migrate("0084", downgrade=True)
    assert await rekey_database.run(retained_state) == before


def seed_origin_checkpoints(connection):
    owner = insert_row(connection, "users", email="origins@example.test", role="user")
    scopes = (
        ({"origin": "briefing"}, "briefing"),
        ({"origin": "subscription", "research_focus": "media"}, "subscription"),
        ({"origin": "research", "research_focus": "media"}, "research"),
        ({"origin": "geolocation"}, "geolocation"),
        ({"research_focus": "media"}, "geolocation"),
        ({"origin": "unknown-origin"}, "research"),
        ({"origin": {"invalid": True}}, "research"),
    )
    summary = {"note": "x" * (MAX_JOB_SUMMARY_BYTES - len(json.dumps({"note": ""})))}
    assert len(json.dumps(summary).encode()) == MAX_JOB_SUMMARY_BYTES
    original = {}
    for scope, origin in scopes:
        payload = {"schema_version": 1, "input": {"scope": scope}, "summary": summary}
        raw = canonical_job_payload(payload)
        job_id = insert_row(
            connection,
            "report_jobs",
            owner_id=owner,
            status="queued",
            stage="queued",
            payload=raw.decode(),
            payload_bytes=len(raw),
            payload_sha256=hashlib.sha256(raw).hexdigest(),
        )
        original[job_id] = raw, summary, origin
    return original


def assert_origin_checkpoint_integrity(connection, original):
    for row in connection.execute(sa.select(table(connection, "report_jobs"))).mappings():
        raw, summary, origin = original[row["id"]]
        assert row["payload"].encode() == raw
        assert row["payload_bytes"] == len(raw)
        assert row["payload_sha256"] == hashlib.sha256(raw).hexdigest()
        # The derived origin belongs to the projection, outside the unchanged
        # checkpoint summary's full 8 KiB allowance.
        assert row["summary"] == {**summary, "origin": origin}


async def test_rekey_preserves_frozen_origins_and_full_summary_allowance(rekey_database):
    await rekey_database.migrate("0081")
    original = await rekey_database.run(seed_origin_checkpoints)
    await rekey_database.migrate("head")
    await rekey_database.run(assert_origin_checkpoint_integrity, original)
