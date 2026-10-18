"""Coalesced public-metadata coverage loss, serialised by the selected-index gate."""

from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.selected_index_models import (
    SelectedIndexLossRow,
    SelectedIndexRecordRow,
)


async def record_removed_rows(
    session: AsyncSession, rows: Sequence[SelectedIndexRecordRow], reason: str, now: datetime
) -> None:
    groups: dict[tuple[UUID, str], list[SelectedIndexRecordRow]] = defaultdict(list)
    for row in rows:
        groups[(row.subscription_id, row.source_id)].append(row)
    for (subscription_id, source_id), removed in groups.items():
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
                    owner_id=sample.owner_id,
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
