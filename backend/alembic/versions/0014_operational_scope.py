"""Personal/team scope with conservative legacy ownership and conflict inventory.

Revision ID: 0014
Revises: 0013

Existing roots remain personal. Existing links and frozen evidence are retained, but
cross-owner/missing references are inventoried in the administrator audit log.
"""

from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None
ROOTS = ("reports", "aois", "collection_plans", "indicators", "schedules", "alerts")


def _key(value: object) -> str:
    return str(value).replace("-", "").lower()


def _inventory() -> None:
    connection = op.get_bind()
    metadata = sa.MetaData()
    tables = {
        name: sa.Table(name, metadata, autoload_with=connection) for name in (*ROOTS, "audit_log")
    }
    owners = {
        name: {
            _key(row.id): _key(row.created_by)
            for row in connection.execute(sa.select(table.c.id, table.c.created_by))
            if row.created_by is not None
        }
        for name, table in tables.items()
        if name != "audit_log"
    }

    def record(source: str, source_id: object, target: str, target_id: object, reason: str) -> None:
        connection.execute(
            tables["audit_log"]
            .insert()
            .values(
                at=datetime.now(UTC),
                actor_user_id=None,
                action="legacy_scope_conflict",
                subject=f"{source}:{source_id}",
                ip=None,
                details={
                    "source_table": source,
                    "source_id": str(source_id),
                    "target_table": target,
                    "target_id": str(target_id),
                    "reason": reason,
                },
            )
        )

    def inspect(
        source: str, source_id: object, owner: object, target: str, target_id: object
    ) -> None:
        if target_id is None:
            return
        target_owner = owners[target].get(_key(target_id))
        if target_owner is None:
            record(source, source_id, target, target_id, "missing_target")
        elif owner is None or _key(owner) != target_owner:
            record(source, source_id, target, target_id, "different_personal_owner")

    relationships = (
        ("collection_plans", "aoi_id", "aois"),
        ("indicators", "plan_id", "collection_plans"),
        ("schedules", "plan_id", "collection_plans"),
        ("schedules", "last_report_id", "reports"),
        ("alerts", "indicator_id", "indicators"),
        ("alerts", "report_id", "reports"),
    )
    for source, field, target in relationships:
        table = tables[source]
        for row in connection.execute(sa.select(table.c.id, table.c.created_by, table.c[field])):
            inspect(source, row[0], row[1], target, row[2])
    reports = tables["reports"]
    for row in connection.execute(sa.select(reports.c.id, reports.c.created_by, reports.c.scope)):
        scope: Any = row[2]
        if isinstance(scope, dict):
            inspect("reports", row[0], row[1], "collection_plans", scope.get("plan"))


def upgrade() -> None:
    for table in ROOTS:
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column("team_id", sa.Uuid(), nullable=True))
            batch.create_foreign_key(f"fk_{table}_team_id_teams", "teams", ["team_id"], ["id"])
            batch.create_index(f"ix_{table}_team_id", ["team_id"])
    op.add_column("alerts", sa.Column("created_by", sa.Uuid(), nullable=True))
    op.create_index("ix_alerts_created_by", "alerts", ["created_by"])
    alerts = sa.table(
        "alerts", sa.column("indicator_id", sa.Uuid()), sa.column("created_by", sa.Uuid())
    )
    indicators = sa.table(
        "indicators", sa.column("id", sa.Uuid()), sa.column("created_by", sa.Uuid())
    )
    op.execute(
        alerts.update().values(
            created_by=sa.select(indicators.c.created_by)
            .where(indicators.c.id == alerts.c.indicator_id)
            .scalar_subquery()
        )
    )
    _inventory()


def downgrade() -> None:
    op.drop_index("ix_alerts_created_by", table_name="alerts")
    op.drop_column("alerts", "created_by")
    for table in reversed(ROOTS):
        with op.batch_alter_table(table) as batch:
            batch.drop_index(f"ix_{table}_team_id")
            batch.drop_constraint(f"fk_{table}_team_id_teams", type_="foreignkey")
            batch.drop_column("team_id")
    # The audit inventory is historical evidence and intentionally survives downgrade.
