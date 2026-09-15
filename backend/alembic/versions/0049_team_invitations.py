"""Add bounded in-app team invitations."""

import sqlalchemy as sa
from alembic import op

revision = "0049"
down_revision = "0048"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "team_invitations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "team_id",
            sa.Uuid(),
            sa.ForeignKey("teams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("recipient_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("inviter_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("note", sa.String(280), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.CheckConstraint(
            "status IN ('pending','accepted','declined','withdrawn','expired')",
            name="ck_team_invitation_status",
        ),
        sa.CheckConstraint("role IN ('member','manager')", name="ck_team_invitation_role"),
        sa.CheckConstraint("revision >= 1", name="ck_team_invitation_revision"),
    )
    op.create_index(
        "ix_team_invitations_recipient_status",
        "team_invitations",
        ["recipient_id", "status"],
    )
    op.create_index("ix_team_invitations_team_status", "team_invitations", ["team_id", "status"])
    op.create_index("ix_team_invitations_expires", "team_invitations", ["expires_at"])
    op.create_index("ix_team_invitations_team", "team_invitations", ["team_id"])
    op.create_index("ix_team_invitations_recipient", "team_invitations", ["recipient_id"])
    op.create_index("ix_team_invitations_inviter", "team_invitations", ["inviter_id"])
    op.create_index(
        "uq_team_invitations_pending_pair",
        "team_invitations",
        ["team_id", "recipient_id"],
        unique=True,
        sqlite_where=sa.text("status = 'pending'"),
        postgresql_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    table = sa.table("team_invitations", sa.column("id"))
    if op.get_bind().scalar(sa.select(sa.func.count()).select_from(table)):
        raise RuntimeError("Refusing downgrade: team invitation records remain.")
    for name in (
        "uq_team_invitations_pending_pair",
        "ix_team_invitations_inviter",
        "ix_team_invitations_recipient",
        "ix_team_invitations_team",
        "ix_team_invitations_expires",
        "ix_team_invitations_team_status",
        "ix_team_invitations_recipient_status",
    ):
        op.drop_index(name, table_name="team_invitations")
    op.drop_table("team_invitations")
