"""Record scoped necessity decisions and preserve permanent account erasure markers."""

import sqlalchemy as sa
from alembic import op

revision = "0095"
down_revision = "0094"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "private_data_reviews",
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("decision", sa.String(12), nullable=False),
        sa.Column("purpose", sa.String(24), nullable=False),
        sa.Column("reviewed_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_review_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("erased_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("revision >= 1", name="ck_private_review_revision"),
        sa.CheckConstraint(
            "decision IN ('retain','hold','remove')", name="ck_private_review_decision"
        ),
        sa.CheckConstraint(
            "purpose IN ('quarterly','account_closure','rights_request','purpose_complete')",
            name="ck_private_review_purpose",
        ),
        sa.CheckConstraint("next_review_at > reviewed_at", name="ck_private_review_dates"),
    )


def downgrade() -> None:
    if op.get_bind().scalar(sa.text("SELECT COUNT(*) FROM private_data_reviews")):
        raise RuntimeError("Cannot downgrade while privacy decisions or erasure markers exist.")
    op.drop_table("private_data_reviews")
