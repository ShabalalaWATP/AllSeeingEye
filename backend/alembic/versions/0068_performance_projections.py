"""Bound baseline history and materialise small polling and monthly-usage projections."""

import hashlib
import json
import logging

import sqlalchemy as sa
from alembic import op

from ase.adapters.persistence.report_job_models import ReportJobRow
from ase.adapters.persistence.report_job_usage_models import ReportJobUsageRow
from ase.adapters.persistence.report_job_usage_projection import usage_rows
from ase.application.report_jobs.budget import JobInterrupted
from ase.domain.report_jobs import canonical_job_payload
from ase.domain.report_search import checked_vector

revision = "0068"
down_revision = "0067"
branch_labels = None
depends_on = None
log = logging.getLogger("alembic.runtime.migration")


def upgrade() -> None:
    # SQLite cannot roll back ALTER TABLE reliably. Reject bad audit rows before DDL.
    for row in _checkpoints():
        _validated(row)
    op.add_column(
        "report_jobs", sa.Column("summary", sa.JSON(), nullable=False, server_default="{}")
    )
    op.add_column(
        "report_embeddings",
        sa.Column("vector_valid", sa.Boolean(), nullable=False, server_default="0"),
    )
    ReportJobUsageRow.__table__.create(op.get_bind())
    op.create_index("ix_activity_samples_hour", "activity_samples", ["hour", "id"])
    op.create_index("ix_llm_usage_user_at", "llm_usage", ["user_id", "at"])
    op.create_index(
        "ix_subscription_attempt_open",
        "subscription_edition_attempts",
        ["started_at", "id"],
        sqlite_where=sa.text("ended_at IS NULL"),
        postgresql_where=sa.text("ended_at IS NULL"),
    )
    _backfill()


def _checkpoints():
    connection = op.get_bind()
    jobs = ReportJobRow.__table__
    cursor = None
    columns = [
        jobs.c[key]
        for key in ("id", "owner_id", "created_at", "payload", "payload_bytes", "payload_sha256")
    ]
    while True:
        query = sa.select(*columns).order_by(jobs.c.id).limit(100)
        if cursor is not None:
            query = query.where(jobs.c.id > cursor)
        rows = connection.execute(query).mappings().all()
        if not rows:
            break
        yield from rows
        cursor = rows[-1]["id"]


def _validated(row):
    try:
        raw = row["payload"].encode("utf-8")
        if (
            len(raw) != row["payload_bytes"]
            or hashlib.sha256(raw).hexdigest() != row["payload_sha256"]
        ):
            raise ValueError("Invalid checkpoint integrity")
        payload = json.loads(raw)
        if canonical_job_payload(payload) != raw:
            raise ValueError("Invalid canonical checkpoint")
        usage = usage_rows(row["id"], row["owner_id"], row["created_at"], payload)
        return payload, usage
    except (ValueError, TypeError, UnicodeError, RecursionError, JobInterrupted) as exc:
        # Fail closed rather than silently undercount an owner's budget.
        log.error("Cannot reconcile report job %s during monthly usage migration", row["id"])
        raise RuntimeError("Repair the reported checkpoint before retrying migration 0068") from exc


def _backfill() -> None:
    connection = op.get_bind()
    jobs = ReportJobRow.__table__
    for row in _checkpoints():
        payload, usage = _validated(row)
        connection.execute(
            jobs.update().where(jobs.c.id == row["id"]).values(summary=payload.get("summary", {}))
        )
        if usage:
            connection.execute(ReportJobUsageRow.__table__.insert(), usage)
    embeddings = sa.Table("report_embeddings", sa.MetaData(), autoload_with=connection)
    for row in connection.execute(sa.select(embeddings.c.report_id, embeddings.c.vector)):
        try:
            checked_vector(row.vector)
        except (ValueError, OverflowError):
            valid = False
        else:
            valid = True
        connection.execute(
            embeddings.update()
            .where(embeddings.c.report_id == row.report_id)
            .values(vector_valid=valid)
        )


def downgrade() -> None:
    op.drop_index("ix_subscription_attempt_open", table_name="subscription_edition_attempts")
    op.drop_index("ix_llm_usage_user_at", table_name="llm_usage")
    op.drop_index("ix_activity_samples_hour", table_name="activity_samples")
    op.drop_table("report_job_monthly_usage")
    with op.batch_alter_table("report_embeddings") as batch:
        batch.drop_column("vector_valid")
    with op.batch_alter_table("report_jobs") as batch:
        batch.drop_column("summary")
