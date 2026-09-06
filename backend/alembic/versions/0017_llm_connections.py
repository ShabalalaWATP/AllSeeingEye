"""Tested AI profile revisions and explicit global/team activation.

Revision ID: 0017
Revises: 0016
"""

import sqlalchemy as sa
from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "llm_binding_sequence",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_llm_binding_sequence_singleton"),
    )
    op.bulk_insert(
        sa.table(
            "llm_binding_sequence", sa.column("id", sa.Integer()), sa.column("value", sa.Integer())
        ),
        [{"id": 1, "value": 0}],
    )
    with op.batch_alter_table("llm_profiles") as batch:
        batch.add_column(sa.Column("reasoning_effort", sa.String(16), nullable=True))
        batch.add_column(sa.Column("revision", sa.Integer(), nullable=False, server_default="1"))
        batch.add_column(sa.Column("tested_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("tested_revision", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("tested_config_hash", sa.String(64), nullable=True))
        batch.add_column(
            sa.Column("test_generation", sa.Integer(), nullable=False, server_default="0")
        )
    op.create_table(
        "llm_connection_bindings",
        sa.Column("scope_key", sa.String(48), primary_key=True),
        sa.Column(
            "team_id",
            sa.Uuid(),
            sa.ForeignKey("teams.id", ondelete="CASCADE"),
            nullable=True,
            unique=True,
        ),
        sa.Column(
            "profile_id",
            sa.Uuid(),
            sa.ForeignKey("llm_profiles.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("profile_revision", sa.Integer(), nullable=False),
        sa.Column("tested_config_hash", sa.String(64), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("activated_by", sa.Uuid(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "(team_id IS NULL AND scope_key = 'global') OR (team_id IS NOT NULL AND scope_key <> 'global')",
            name="ck_llm_binding_scope",
        ),
    )
    op.create_index(
        "ix_llm_connection_bindings_profile_id", "llm_connection_bindings", ["profile_id"]
    )


def downgrade() -> None:
    bindings = sa.table("llm_connection_bindings", sa.column("scope_key", sa.String(48)))
    if op.get_bind().scalar(sa.select(sa.func.count()).select_from(bindings)):
        raise RuntimeError(
            "Cannot downgrade while AI connection bindings exist; preserve and explicitly resolve them first."
        )
    profiles = sa.table("llm_profiles", sa.column("reasoning_effort", sa.String(16)))
    if op.get_bind().scalar(
        sa.select(sa.func.count())
        .select_from(profiles)
        .where(profiles.c.reasoning_effort.is_not(None))
    ):
        raise RuntimeError(
            "Cannot downgrade while explicit reasoning settings exist; preserve and explicitly resolve them first."
        )
    op.drop_table("llm_connection_bindings")
    op.drop_table("llm_binding_sequence")
    with op.batch_alter_table("llm_profiles") as batch:
        for name in (
            "test_generation",
            "tested_config_hash",
            "tested_revision",
            "tested_at",
            "revision",
            "reasoning_effort",
        ):
            batch.drop_column(name)
