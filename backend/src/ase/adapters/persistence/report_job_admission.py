"""Database expressions that enforce owner-fair durable report admission."""

from uuid import UUID

from sqlalchemy import ColumnElement, Select, func, select
from sqlalchemy.orm import aliased

from ase.adapters.persistence.report_job_models import ReportJobRow as Row


def fair_queued_ids(limit: int) -> Select[tuple[UUID]]:
    running = (
        select(Row.owner_id.label("owner_id"), func.count().label("running_count"))
        .where(Row.status == "running")
        .group_by(Row.owner_id)
        .subquery()
    )
    ranked = (
        select(
            Row.id.label("id"),
            Row.owner_id.label("owner_id"),
            Row.created_at.label("created_at"),
            func.row_number()
            .over(partition_by=Row.owner_id, order_by=(Row.created_at, Row.id))
            .label("owner_rank"),
        )
        .where(Row.status == "queued")
        .subquery()
    )
    return (
        select(ranked.c.id)
        .outerjoin(running, running.c.owner_id == ranked.c.owner_id)
        .where(ranked.c.owner_rank == 1, func.coalesce(running.c.running_count, 0) == 0)
        .order_by(ranked.c.created_at, ranked.c.id)
        .limit(limit)
    )


def no_running_sibling() -> ColumnElement[bool]:
    other = aliased(Row)
    return (
        ~select(other.id)
        .where(
            other.owner_id == Row.owner_id,
            other.status == "running",
            other.id != Row.id,
        )
        .exists()
    )
