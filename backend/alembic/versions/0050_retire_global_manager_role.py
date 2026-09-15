"""Retire the legacy global Manager account role.

Revision ID: 0050
Revises: 0049

Team management is represented by team memberships.  Existing global Manager
values are therefore converted to ordinary users while their team membership
roles remain unchanged.  Security versions are bumped so sessions issued under
the old global role cannot be reused after the migration.
"""

import sqlalchemy as sa
from alembic import op

revision = "0050"
down_revision = "0049"
branch_labels = None
depends_on = None


def upgrade() -> None:
    users = sa.table(
        "users",
        sa.column("role", sa.String(16)),
        sa.column("security_version", sa.Integer()),
    )
    op.execute(
        sa.update(users)
        .where(users.c.role == "manager")
        .values(role="user", security_version=users.c.security_version + 1)
    )


def downgrade() -> None:
    # The conversion is intentionally one-way.  Restoring a global role would
    # silently grant authority that now belongs to explicit team membership.
    pass
