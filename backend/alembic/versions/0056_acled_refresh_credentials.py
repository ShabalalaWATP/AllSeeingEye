"""Store the rotated ACLED OAuth refresh token encrypted in a single-row table."""

import sqlalchemy as sa
from alembic import op

revision = "0056"
down_revision: str | None = "0054"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "acled_credentials",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("refresh_token_encrypted", sa.Text(), nullable=False),
        sa.Column("environment_fingerprint", sa.String(64), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_acled_credentials_singleton"),
    )


def downgrade() -> None:
    table = sa.table("acled_credentials", sa.column("id"))
    if op.get_bind().scalar(sa.select(sa.func.count()).select_from(table)):
        raise RuntimeError(
            "Refusing downgrade: a rotated ACLED refresh token remains. Delete the "
            "acled_credentials row deliberately first; the environment token may be stale."
        )
    op.drop_table("acled_credentials")
