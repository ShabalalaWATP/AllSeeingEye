"""Personal workspace AI assignments without changing existing team or global routes.

Revision ID: 0028
Revises: 0027
"""

import sqlalchemy as sa
from alembic import op

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None


SCOPE = (
    "(team_id IS NULL AND user_id IS NULL AND scope_key = 'global') OR "
    "(team_id IS NOT NULL AND user_id IS NULL AND scope_key LIKE 'team:%') OR "
    "(team_id IS NULL AND user_id IS NOT NULL AND scope_key LIKE 'user:%')"
)


def upgrade() -> None:
    with op.batch_alter_table("llm_connection_bindings") as batch:
        batch.add_column(sa.Column("user_id", sa.Uuid(), nullable=True))
        batch.create_foreign_key(
            "fk_llm_binding_user", "users", ["user_id"], ["id"], ondelete="CASCADE"
        )
        batch.create_unique_constraint("uq_llm_binding_user", ["user_id"])
        batch.drop_constraint("ck_llm_binding_scope", type_="check")
        batch.create_check_constraint("ck_llm_binding_scope", SCOPE)


def downgrade() -> None:
    bindings = sa.table("llm_connection_bindings", sa.column("user_id", sa.Uuid()))
    if op.get_bind().scalar(
        sa.select(sa.func.count()).select_from(bindings).where(bindings.c.user_id.is_not(None))
    ):
        raise RuntimeError(
            "Cannot downgrade while personal AI overrides exist; reset them explicitly first."
        )
    with op.batch_alter_table("llm_connection_bindings") as batch:
        batch.drop_constraint("ck_llm_binding_scope", type_="check")
        batch.drop_constraint("uq_llm_binding_user", type_="unique")
        batch.drop_constraint("fk_llm_binding_user", type_="foreignkey")
        batch.drop_column("user_id")
        batch.create_check_constraint(
            "ck_llm_binding_scope",
            "(team_id IS NULL AND scope_key = 'global') OR (team_id IS NOT NULL AND scope_key <> 'global')",
        )
