"""Stable, bounded SQL pages with one overdue item per owner before the next."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, not_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.operational_models import ScheduleRow
from ase.adapters.persistence.subscription_edition_models import SubscriptionEditionRow
from ase.application.schedules.edition_planning import BUDGET_BLOCK_REASON, BUDGET_RETRY_AFTER
from ase.application.schedules.runner import DueCursor
from ase.domain.report_jobs import job_timestamp
from ase.domain.subscription_editions import EditionWorkflow


def _after(rank: Any, owner: Any, item: Any, cursor: DueCursor) -> Any:
    return or_(
        rank > cursor.owner_rank,
        and_(rank == cursor.owner_rank, owner > cursor.owner_id),
        and_(
            rank == cursor.owner_rank,
            owner == cursor.owner_id,
            item > cursor.item_id,
        ),
    )


async def _page(
    session: AsyncSession,
    statement: Any,
    rank: Any,
    owner: Any,
    item: Any,
    *,
    limit: int,
    cursor: DueCursor | None,
) -> tuple[list[Any], DueCursor | None]:
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("Choose a bounded due batch of 1 to 100 items.")
    ordered = statement.order_by(rank, owner, item)
    if cursor is None:
        rows = list((await session.execute(ordered.limit(limit))).all())
    else:
        predicate = _after(rank, owner, item, cursor)
        rows = list((await session.execute(ordered.where(predicate).limit(limit))).all())
        if len(rows) < limit:
            rows.extend(
                (
                    await session.execute(ordered.where(not_(predicate)).limit(limit - len(rows)))
                ).all()
            )
    last = rows[-1] if rows else None
    next_cursor = DueCursor(int(last[1]), last[2], last[3]) if last is not None else cursor
    return rows, next_cursor


async def due_schedule_rows(
    session: AsyncSession,
    now: datetime,
    *,
    limit: int,
    cursor: DueCursor | None,
) -> tuple[list[ScheduleRow], DueCursor | None]:
    job_timestamp(now)
    ranked = (
        select(
            ScheduleRow.id.label("item_id"),
            ScheduleRow.created_by.label("owner_id"),
            func.row_number()
            .over(
                partition_by=ScheduleRow.created_by,
                order_by=(ScheduleRow.next_run_at, ScheduleRow.id),
            )
            .label("owner_rank"),
        )
        .where(
            ScheduleRow.enabled.is_(True),
            ScheduleRow.archived_at.is_(None),
            ScheduleRow.next_run_at <= now,
        )
        .subquery()
    )
    statement = select(ScheduleRow, ranked.c.owner_rank, ranked.c.owner_id, ranked.c.item_id).join(
        ranked, ScheduleRow.id == ranked.c.item_id
    )
    rows, next_cursor = await _page(
        session,
        statement,
        ranked.c.owner_rank,
        ranked.c.owner_id,
        ranked.c.item_id,
        limit=limit,
        cursor=cursor,
    )
    return [row[0] for row in rows], next_cursor


async def due_edition_rows(
    session: AsyncSession,
    now: datetime,
    *,
    limit: int,
    cursor: DueCursor | None,
) -> tuple[list[tuple[SubscriptionEditionRow, UUID]], DueCursor | None]:
    job_timestamp(now)
    due_at = func.coalesce(SubscriptionEditionRow.due_at_utc, SubscriptionEditionRow.created_at)
    pending = and_(
        SubscriptionEditionRow.workflow == EditionWorkflow.PENDING.value,
        or_(SubscriptionEditionRow.due_at_utc.is_(None), SubscriptionEditionRow.due_at_utc <= now),
    )
    budget_retry = and_(
        SubscriptionEditionRow.workflow == EditionWorkflow.BLOCKED.value,
        SubscriptionEditionRow.job_id.is_(None),
        SubscriptionEditionRow.safe_reason == BUDGET_BLOCK_REASON,
        SubscriptionEditionRow.updated_at <= now - BUDGET_RETRY_AFTER,
    )
    ranked = (
        select(
            SubscriptionEditionRow.id.label("item_id"),
            ScheduleRow.created_by.label("owner_id"),
            func.row_number()
            .over(
                partition_by=ScheduleRow.created_by,
                order_by=(due_at, SubscriptionEditionRow.id),
            )
            .label("owner_rank"),
        )
        .join(ScheduleRow, SubscriptionEditionRow.subscription_id == ScheduleRow.id)
        .where(
            or_(pending, budget_retry),
            ScheduleRow.enabled.is_(True),
            ScheduleRow.archived_at.is_(None),
        )
        .subquery()
    )
    statement = select(
        SubscriptionEditionRow, ranked.c.owner_rank, ranked.c.owner_id, ranked.c.item_id
    ).join(ranked, SubscriptionEditionRow.id == ranked.c.item_id)
    rows, next_cursor = await _page(
        session,
        statement,
        ranked.c.owner_rank,
        ranked.c.owner_id,
        ranked.c.item_id,
        limit=limit,
        cursor=cursor,
    )
    return [(row[0], row[2]) for row in rows], next_cursor
