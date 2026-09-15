"""Immutable Research Brief revisions and optional schedule/job pins."""

import sqlalchemy as sa
from alembic import op

revision = "0036"
down_revision = "0035"
branch_labels = None
depends_on = None

_BRIEF_TABLE = "research_brief_revisions"


def _add_brief_reference(table: str) -> None:
    with op.batch_alter_table(table) as batch:
        batch.add_column(sa.Column("brief_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("brief_revision", sa.Integer(), nullable=True))
        batch.create_check_constraint(
            f"ck_{table}_brief_pair",
            "(brief_id IS NULL AND brief_revision IS NULL) OR "
            "(brief_id IS NOT NULL AND brief_revision >= 1)",
        )
        batch.create_foreign_key(
            f"fk_{table}_brief_revision",
            _BRIEF_TABLE,
            ["brief_id", "brief_revision"],
            ["brief_id", "revision"],
        )


def upgrade() -> None:
    op.create_table(
        _BRIEF_TABLE,
        sa.Column("brief_id", sa.Uuid(), primary_key=True),
        sa.Column("revision", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("team_id", sa.Uuid(), sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("origin", sa.String(20), nullable=False),
        sa.Column("published", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revised_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("payload_sha256", sa.String(64), nullable=False),
        sa.Column("payload_bytes", sa.Integer(), nullable=False),
        sa.CheckConstraint("revision >= 1", name="ck_research_brief_revision"),
        sa.CheckConstraint("schema_version = 1", name="ck_research_brief_schema"),
        sa.CheckConstraint(
            "payload_bytes BETWEEN 2 AND 786432", name="ck_research_brief_payload_size"
        ),
        sa.CheckConstraint("length(payload_sha256) = 64", name="ck_research_brief_digest_length"),
        sa.CheckConstraint(
            "origin IN ('authored','legacy-derived')", name="ck_research_brief_origin"
        ),
    )
    op.create_index(
        "ix_research_brief_owner_latest", _BRIEF_TABLE, ["owner_id", "revised_at", "brief_id"]
    )
    op.create_index(
        "ix_research_brief_team_latest", _BRIEF_TABLE, ["team_id", "revised_at", "brief_id"]
    )
    _add_brief_reference("schedules")
    _add_brief_reference("report_jobs")


def _drop_brief_reference(table: str) -> None:
    with op.batch_alter_table(table) as batch:
        batch.drop_constraint(f"fk_{table}_brief_revision", type_="foreignkey")
        batch.drop_constraint(f"ck_{table}_brief_pair", type_="check")
        batch.drop_column("brief_revision")
        batch.drop_column("brief_id")


def downgrade() -> None:
    connection = op.get_bind()
    brief_rows = sa.table(_BRIEF_TABLE, sa.column("brief_id"))
    if connection.scalar(sa.select(sa.func.count()).select_from(brief_rows)):
        raise RuntimeError("Refusing downgrade: retained Research Brief revisions remain.")
    for table in ("schedules", "report_jobs"):
        refs = sa.table(table, sa.column("brief_id"))
        if connection.scalar(
            sa.select(sa.func.count()).select_from(refs).where(refs.c.brief_id.is_not(None))
        ):
            raise RuntimeError("Refusing downgrade: retained Research Brief references remain.")
    _drop_brief_reference("report_jobs")
    _drop_brief_reference("schedules")
    op.drop_index("ix_research_brief_team_latest", table_name=_BRIEF_TABLE)
    op.drop_index("ix_research_brief_owner_latest", table_name=_BRIEF_TABLE)
    op.drop_table(_BRIEF_TABLE)
