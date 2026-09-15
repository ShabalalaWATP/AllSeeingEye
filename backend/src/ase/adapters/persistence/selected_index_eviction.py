"""Quota eviction inside a selected-index page transaction."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.selected_index_models import (
    SelectedIndexLossRow,
    SelectedIndexRecordRow,
)
from ase.domain.errors import Conflict
from ase.domain.selected_subscription_index import SelectedIndexLimits

GAP_REASONS = frozenset(
    {
        "source_outage",
        "source_disabled",
        "cache_truncated",
        "retention_horizon",
        "initial_history_gap",
    }
)


async def record_index_gap(
    session: AsyncSession,
    *,
    subscription_id: UUID,
    owner_id: UUID,
    team_id: UUID | None,
    source_id: str,
    reason: str,
    start: datetime,
    end: datetime,
    now: datetime,
) -> None:
    """Coalesce an unknown-item coverage interval without claiming items were lost."""

    if reason not in GAP_REASONS or start >= end:
        raise ValueError("Invalid selected-index coverage gap")
    existing = await session.scalar(
        select(SelectedIndexLossRow).where(
            SelectedIndexLossRow.subscription_id == subscription_id,
            SelectedIndexLossRow.source_id == source_id,
            SelectedIndexLossRow.reason == reason,
        )
    )
    if existing is None:
        session.add(
            SelectedIndexLossRow(
                subscription_id=subscription_id,
                owner_id=owner_id,
                team_id=team_id,
                source_id=source_id,
                reason=reason,
                lost_items=0,
                earliest_event_at=start,
                latest_event_at=end,
                occurred_at=now,
            )
        )
    else:
        existing.earliest_event_at = min(existing.earliest_event_at, start)
        existing.latest_event_at = max(existing.latest_event_at, end)
        existing.occurred_at = now
    await session.flush()


async def enforce_owner_limits(
    session: AsyncSession, *, owner_id: UUID, now: datetime, limits: SelectedIndexLimits
) -> None:
    """Evict only this owner's oldest records and record the resulting coverage loss."""

    rows = (
        await session.scalars(
            select(SelectedIndexRecordRow)
            .where(SelectedIndexRecordRow.owner_id == owner_id)
            .order_by(SelectedIndexRecordRow.first_seen_at, SelectedIndexRecordRow.id)
        )
    ).all()
    retained = list(rows)
    losses: dict[tuple[UUID, str, str], list[SelectedIndexRecordRow]] = defaultdict(list)

    for row in rows:
        if min(row.expires_at, row.first_seen_at + timedelta(days=limits.max_age_days)) <= now:
            retained.remove(row)
            losses[(row.subscription_id, row.source_id, "age")].append(row)

    total_bytes = sum(row.stored_bytes for row in retained)
    while retained and (len(retained) > limits.owner_records or total_bytes > limits.owner_bytes):
        reason = "owner_item_cap" if len(retained) > limits.owner_records else "owner_byte_cap"
        row = retained.pop(0)
        total_bytes -= row.stored_bytes
        losses[(row.subscription_id, row.source_id, reason)].append(row)

    for (subscription_id, source_id, reason), removed in losses.items():
        for row in removed:
            await session.delete(row)
        event_times = [row.published_at or row.observed_at or row.first_seen_at for row in removed]
        existing = await session.scalar(
            select(SelectedIndexLossRow).where(
                SelectedIndexLossRow.subscription_id == subscription_id,
                SelectedIndexLossRow.source_id == source_id,
                SelectedIndexLossRow.reason == reason,
            )
        )
        if existing is None:
            sample = removed[0]
            session.add(
                SelectedIndexLossRow(
                    subscription_id=subscription_id,
                    owner_id=owner_id,
                    team_id=sample.team_id,
                    source_id=source_id,
                    reason=reason,
                    lost_items=len(removed),
                    earliest_event_at=min(event_times),
                    latest_event_at=max(event_times),
                    occurred_at=now,
                )
            )
        else:
            existing.lost_items += len(removed)
            existing.earliest_event_at = min(existing.earliest_event_at, *event_times)
            existing.latest_event_at = max(existing.latest_event_at, *event_times)
            existing.occurred_at = now
    await session.flush()

    aggregate_bytes = await session.scalar(select(func.sum(SelectedIndexRecordRow.stored_bytes)))
    if (aggregate_bytes or 0) > limits.aggregate_bytes:
        raise Conflict("Selected-index aggregate byte ceiling is full; page was not retained.")
