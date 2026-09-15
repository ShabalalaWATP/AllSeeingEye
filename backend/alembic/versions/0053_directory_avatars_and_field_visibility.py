"""Add per-field directory visibility and bounded, re-encoded directory avatars."""

import sqlalchemy as sa
from alembic import op

revision = "0053"
down_revision: str | None = "0052"
branch_labels = None
depends_on = None

# Existing rows showed these fields whenever set, so they migrate as visible.
_VISIBLE_BY_DEFAULT = (
    "show_job_title",
    "show_organisation",
    "show_biography",
    "show_country",
    "show_languages",
    "show_expertise",
)


def upgrade() -> None:
    with op.batch_alter_table("directory_profiles") as batch:
        for column in _VISIBLE_BY_DEFAULT:
            batch.add_column(
                sa.Column(column, sa.Boolean(), nullable=False, server_default=sa.true())
            )
        batch.add_column(sa.Column("avatar_sha256", sa.String(64), nullable=True))
    op.create_table(
        "directory_avatars",
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("content_type", sa.String(16), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("byte_count", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "byte_count > 0 AND byte_count <= 262144", name="ck_directory_avatar_bytes"
        ),
        sa.CheckConstraint(
            "width > 0 AND width <= 256 AND height > 0 AND height <= 256",
            name="ck_directory_avatar_dimensions",
        ),
        sa.CheckConstraint(
            "content_type IN ('image/webp', 'image/png')", name="ck_directory_avatar_type"
        ),
    )


def downgrade() -> None:
    avatars = sa.table("directory_avatars", sa.column("user_id"))
    if op.get_bind().scalar(sa.select(sa.func.count()).select_from(avatars)):
        raise RuntimeError("Refusing downgrade: directory avatars remain.")
    profiles = sa.table(
        "directory_profiles", *(sa.column(name, sa.Boolean()) for name in _VISIBLE_BY_DEFAULT)
    )
    hidden = sa.or_(*(profiles.c[name].is_(sa.false()) for name in _VISIBLE_BY_DEFAULT))
    if op.get_bind().scalar(sa.select(sa.func.count()).select_from(profiles).where(hidden)):
        # The earlier schema would publish these fields again, widening visibility.
        raise RuntimeError("Refusing downgrade: hidden directory fields remain.")
    op.drop_table("directory_avatars")
    with op.batch_alter_table("directory_profiles") as batch:
        batch.drop_column("avatar_sha256")
        for column in reversed(_VISIBLE_BY_DEFAULT):
            batch.drop_column(column)
