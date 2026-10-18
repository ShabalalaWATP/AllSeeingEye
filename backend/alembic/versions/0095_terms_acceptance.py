"""Record which Terms version an account request and an account accepted, and when.

Existing rows keep null values: those accounts are asked to accept on their next visit.
"""

import sqlalchemy as sa
from alembic import op

revision = "0095"
down_revision = "0094"
branch_labels = None
depends_on = None

TABLES = ("users", "account_requests")


def upgrade() -> None:
    for table in TABLES:
        op.add_column(table, sa.Column("terms_version", sa.String(32), nullable=True))
        op.add_column(
            table, sa.Column("terms_accepted_at", sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    bind = op.get_bind()
    for statement in (
        "SELECT COUNT(*) FROM users WHERE terms_accepted_at IS NOT NULL",
        "SELECT COUNT(*) FROM account_requests WHERE terms_accepted_at IS NOT NULL",
    ):
        # Dropping the columns would silently discard evidence of what people agreed to.
        if bind.scalar(sa.text(statement)):
            raise RuntimeError("Cannot downgrade while recorded terms acceptance is retained.")
    for table in TABLES:
        with op.batch_alter_table(table) as batch:
            batch.drop_column("terms_accepted_at")
            batch.drop_column("terms_version")
