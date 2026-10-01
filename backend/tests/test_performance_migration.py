"""Migration 0083 preserves audit payloads and backfills small projections."""

import hashlib
import json
import sqlite3
from contextlib import closing
from uuid import uuid4

import pytest
from alembic import command

from test_mfa_migration import prepare


def seeded_checkpoint(tmp_path):
    config, database, owner = prepare(tmp_path)
    command.upgrade(config, "0082")
    job_id = uuid4().hex
    payload = json.dumps(
        {
            "schema_version": 1,
            "summary": {"completed_sections": 7},
            "calls": [
                {
                    "status": "in_flight",
                    "reserved_output": 100,
                    "dispatched_at": "2026-09-01T12:00:00+00:00",
                }
            ],
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute(
            "INSERT INTO report_jobs (id,request_key,owner_id,title,status,stage,created_at,"
            "updated_at,revision,payload,payload_sha256,payload_bytes,report_id,version_id) "
            "VALUES (?,?,?,'Fixture','queued','queued',?,?,1,?,?,?,?,?)",
            (
                job_id,
                uuid4().hex,
                owner,
                "2026-09-01 12:00:00",
                "2026-09-01 12:00:00",
                payload,
                hashlib.sha256(payload.encode()).hexdigest(),
                len(payload),
                uuid4().hex,
                uuid4().hex,
            ),
        )
    return config, database, payload


def test_upgrade_backfills_usage_summary_and_downgrade_keeps_audit(tmp_path):
    config, database, payload = seeded_checkpoint(tmp_path)
    command.upgrade(config, "0083")
    with closing(sqlite3.connect(database)) as connection:
        summary, retained = connection.execute("SELECT summary,payload FROM report_jobs").fetchone()
        assert json.loads(summary) == {"completed_sections": 7} and retained == payload
        assert connection.execute(
            "SELECT owner_requests,owner_output_tokens,subscription_requests,"
            "subscription_output_tokens FROM report_job_monthly_usage"
        ).fetchone() == (1, 100, 1, 100)
        assert "ix_activity_samples_hour" in {
            row[1] for row in connection.execute("PRAGMA index_list(activity_samples)")
        }
    command.downgrade(config, "0082")
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT payload FROM report_jobs").fetchone() == (payload,)
    command.upgrade(config, "0083")


@pytest.mark.parametrize("corruption", ["digest", "calls"])
def test_bad_checkpoint_stops_migration_before_sqlite_schema_changes(tmp_path, corruption):
    config, database, original = seeded_checkpoint(tmp_path)
    with closing(sqlite3.connect(database)) as connection, connection:
        if corruption == "digest":
            connection.execute("UPDATE report_jobs SET payload_sha256=?", ("0" * 64,))
        else:
            raw = json.dumps(
                {"schema_version": 1, "calls": [{"status": "in_flight"}]},
                sort_keys=True,
                separators=(",", ":"),
            )
            connection.execute(
                "UPDATE report_jobs SET payload=?,payload_bytes=?,payload_sha256=?",
                (raw, len(raw), hashlib.sha256(raw.encode()).hexdigest()),
            )
    with pytest.raises(RuntimeError, match="Repair the reported checkpoint"):
        command.upgrade(config, "0083")
    with closing(sqlite3.connect(database)) as connection, connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == ("0082",)
        assert "summary" not in {
            row[1] for row in connection.execute("PRAGMA table_info(report_jobs)")
        }
        assert not connection.execute(
            "SELECT name FROM sqlite_master WHERE name='report_job_monthly_usage'"
        ).fetchall()
        connection.execute(
            "UPDATE report_jobs SET payload=?,payload_bytes=?,payload_sha256=?",
            (original, len(original), hashlib.sha256(original.encode()).hexdigest()),
        )
    command.upgrade(config, "0083")
