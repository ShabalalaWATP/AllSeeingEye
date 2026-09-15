"""Add owner-controlled, opt-in searchable directory profiles."""

import sqlalchemy as sa
from alembic import op

revision = "0036"
down_revision = "0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "directory_profiles",
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("username", sa.String(32), nullable=True),
        sa.Column("job_title", sa.String(120), nullable=True),
        sa.Column("organisation", sa.String(120), nullable=True),
        sa.Column("biography", sa.Text(), nullable=True),
        sa.Column("country", sa.String(2), nullable=True),
        sa.Column("languages", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("expertise", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("timezone", sa.String(100), nullable=True),
        sa.Column("is_discoverable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("show_timezone", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("revision > 0", name="ck_directory_profile_revision"),
        sa.CheckConstraint(
            "country IS NULL OR length(country) = 2", name="ck_directory_profile_country"
        ),
    )
    op.create_index(
        "ix_directory_profiles_username",
        "directory_profiles",
        ["username"],
        unique=True,
    )
    op.create_index(
        "ix_directory_profiles_discoverable",
        "directory_profiles",
        ["is_discoverable", "username"],
    )
    op.create_index(
        "ix_directory_profiles_organisation",
        "directory_profiles",
        ["organisation"],
    )


def downgrade() -> None:
    table = sa.table("directory_profiles", sa.column("user_id"))
    if op.get_bind().scalar(sa.select(sa.func.count()).select_from(table)):
        raise RuntimeError("Refusing downgrade: directory profiles remain.")
    op.drop_index("ix_directory_profiles_organisation", table_name="directory_profiles")
    op.drop_index("ix_directory_profiles_discoverable", table_name="directory_profiles")
    op.drop_index("ix_directory_profiles_username", table_name="directory_profiles")
    op.drop_table("directory_profiles")
