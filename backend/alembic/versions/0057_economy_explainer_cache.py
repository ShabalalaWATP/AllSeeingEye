"""Cache the generated plain-English economy explainer as a small operational aggregate."""

import sqlalchemy as sa
from alembic import op

revision = "0057"
down_revision: str | None = "0056"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "economy_explainers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("model", sa.String(255), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("snapshot_fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
    )
    op.create_index("ix_economy_explainers_fingerprint", "economy_explainers", ["fingerprint"])
    op.create_index("ix_economy_explainers_generated_at", "economy_explainers", ["generated_at"])


def downgrade() -> None:
    # Only regenerable generated text is held here, so the table is simply dropped.
    op.drop_index("ix_economy_explainers_generated_at", table_name="economy_explainers")
    op.drop_index("ix_economy_explainers_fingerprint", table_name="economy_explainers")
    op.drop_table("economy_explainers")
