"""Private public-site enquiries. Apply through the reviewed migration workflow."""

import sqlalchemy as sa
from alembic import op

revision = "0093"
down_revision = "0092"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "enterprise_enquiries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("organisation", sa.String(150), nullable=False),
        sa.Column("role", sa.String(100), nullable=False),
        sa.Column("deployment_interest", sa.String(20), nullable=False),
        sa.Column("expected_users", sa.String(10), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submission_key", sa.String(64), nullable=False, unique=True),
    )
    op.create_index("ix_enterprise_enquiries_status", "enterprise_enquiries", ["status"])
    op.create_index("ix_enterprise_enquiries_created_at", "enterprise_enquiries", ["created_at"])


def downgrade() -> None:
    if op.get_bind().scalar(sa.text("SELECT COUNT(*) FROM enterprise_enquiries")):
        raise RuntimeError("Export or explicitly remove enquiries before downgrading.")
    op.drop_table("enterprise_enquiries")
