"""Separate opaque sender submissions from private invitation delivery state."""

import sqlalchemy as sa
from alembic import op

revision = "0067"
down_revision = "0066"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "team_invitation_receipts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "invitation_id",
            sa.Uuid(),
            sa.ForeignKey("team_invitations.id", ondelete="SET NULL"),
            nullable=True,
            unique=True,
        ),
        sa.Column(
            "team_id", sa.Uuid(), sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("inviter_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("recipient_id", sa.Uuid(), nullable=True),
        sa.Column("recipient_display_name", sa.String(100), nullable=True),
        sa.Column("recipient_username", sa.String(32), nullable=True),
        sa.Column("note", sa.String(280), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.CheckConstraint(
            "status IN ('pending','accepted','withdrawn')", name="ck_invitation_receipt_status"
        ),
        sa.CheckConstraint("revision >= 1", name="ck_invitation_receipt_revision"),
    )
    op.create_index(
        "ix_invitation_receipts_team_status", "team_invitation_receipts", ["team_id", "status"]
    )
    # Historical unknown submissions were never stored. Only accepted deliveries
    # have consent to become visible; unaccepted deliveries remain in recipients'
    # inboxes. Never reconstruct an old submitted handle from a current profile.
    op.execute(
        sa.text("""INSERT INTO team_invitation_receipts
        (id, invitation_id, team_id, inviter_id, recipient_id, note, status,
         created_at, expires_at, responded_at, revision)
        SELECT id, id, team_id, inviter_id, recipient_id, note, status,
               created_at, expires_at, responded_at, revision
        FROM team_invitations WHERE status = 'accepted'""")
    )


def downgrade() -> None:
    raise RuntimeError(
        "Sender receipts preserve privacy and withdrawal state; restore a reviewed matching backup to downgrade."
    )
