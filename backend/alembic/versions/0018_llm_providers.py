"""Native provider profiles and longer encrypted credentials without changing activation.

Revision ID: 0018
Revises: 0017
"""

import sqlalchemy as sa
from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def _check_historical_routing(connection: sa.Connection) -> None:
    versions = sa.table(
        "report_versions", sa.column("id", sa.Uuid()), sa.column("analysis", sa.JSON())
    )
    statement = sa.select(versions.c.id, versions.c.analysis).order_by(versions.c.id).limit(100)
    last_id = None
    try:
        while True:
            page = statement if last_id is None else statement.where(versions.c.id > last_id)
            # Bound memory without an asyncpg server cursor surviving into subsequent DDL.
            with connection.execute(page) as result:
                rows = result.all()
            if not rows:
                break
            last_id = rows[-1].id
            for _, analysis in rows:
                if analysis is None:
                    continue
                if not isinstance(analysis, dict):
                    raise ValueError
                routing = analysis.get("model_routing")
                if routing is None:
                    continue
                if not isinstance(routing, dict) or not isinstance(routing.get("profiles"), list):
                    raise ValueError
                profiles = routing["profiles"]
                if not 1 <= len(profiles) <= 4:
                    raise ValueError
                if any(
                    not isinstance(profile, dict) or "provider" in profile for profile in profiles
                ):
                    raise ValueError
    except (ValueError, TypeError):
        raise RuntimeError(
            "Cannot downgrade while historical routing contains provider metadata or unreadable data."
        ) from None


def upgrade() -> None:
    with op.batch_alter_table("llm_profiles") as batch:
        batch.add_column(
            sa.Column("provider", sa.String(32), nullable=False, server_default="openai_compatible")
        )
        batch.alter_column(
            "api_key_encrypted",
            existing_type=sa.String(2048),
            type_=sa.Text(),
            existing_nullable=False,
        )
        batch.alter_column(
            "model", existing_type=sa.String(120), type_=sa.String(2048), existing_nullable=False
        )
    with op.batch_alter_table("report_versions") as batch:
        batch.alter_column(
            "model", existing_type=sa.String(120), type_=sa.String(2048), existing_nullable=False
        )


def downgrade() -> None:
    profiles = sa.table(
        "llm_profiles",
        sa.column("provider", sa.String(32)),
        sa.column("api_key_encrypted", sa.Text()),
        sa.column("model", sa.String(2048)),
    )
    connection = op.get_bind()
    if connection.scalar(
        sa.select(sa.func.count())
        .select_from(profiles)
        .where(profiles.c.provider != "openai_compatible")
    ):
        raise RuntimeError("Cannot downgrade while native provider profiles exist.")
    if connection.scalar(
        sa.select(sa.func.count())
        .select_from(profiles)
        .where(sa.func.length(profiles.c.api_key_encrypted) > 2048)
    ):
        raise RuntimeError("Cannot downgrade while encrypted credentials exceed 2048 characters.")
    if connection.scalar(
        sa.select(sa.func.count())
        .select_from(profiles)
        .where(sa.func.length(profiles.c.model) > 120)
    ):
        raise RuntimeError("Cannot downgrade while model identifiers exceed 120 characters.")
    versions = sa.table("report_versions", sa.column("model", sa.String(2048)))
    if connection.scalar(
        sa.select(sa.func.count())
        .select_from(versions)
        .where(sa.func.length(versions.c.model) > 120)
    ):
        raise RuntimeError(
            "Cannot downgrade while historical report model identifiers exceed 120 characters."
        )
    # The previous strict codec rejects provider fields, including OpenAI defaults.
    # Keep frozen evidence unchanged and refuse ambiguous/corrupt history conservatively.
    _check_historical_routing(connection)
    # All checks precede DDL, including on SQLite where DDL is not transactional.
    with op.batch_alter_table("llm_profiles") as batch:
        batch.drop_column("provider")
        batch.alter_column(
            "api_key_encrypted",
            existing_type=sa.Text(),
            type_=sa.String(2048),
            existing_nullable=False,
        )
        batch.alter_column(
            "model", existing_type=sa.String(2048), type_=sa.String(120), existing_nullable=False
        )
    with op.batch_alter_table("report_versions") as batch:
        batch.alter_column(
            "model", existing_type=sa.String(2048), type_=sa.String(120), existing_nullable=False
        )
