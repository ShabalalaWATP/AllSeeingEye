"""Remember explicit analytical baseline acceptance on historical editions."""

import sqlalchemy as sa
from alembic import op

revision = "0038"
down_revision = "0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("subscription_editions") as batch:
        batch.add_column(
            sa.Column(
                "accepted_as_baseline", sa.Boolean(), nullable=False, server_default=sa.false()
            )
        )


def downgrade() -> None:
    accepted = (
        op.get_bind()
        .execute(sa.text("SELECT 1 FROM subscription_editions WHERE accepted_as_baseline LIMIT 1"))
        .first()
    )
    if accepted is not None:
        raise RuntimeError("Downgrade would lose audited baseline acceptance history.")
    with op.batch_alter_table("subscription_editions") as batch:
        batch.drop_column("accepted_as_baseline")
