"""Independent rotating expiry, including metadata owned by dormant accounts."""

from datetime import datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.selected_index_losses import record_removed_rows
from ase.adapters.persistence.selected_index_models import (
    SelectedIndexGateRow,
    SelectedIndexRecordRow,
)
from ase.adapters.persistence.users import SqlUserRepository
from ase.domain.errors import Conflict
from ase.domain.selected_subscription_index import SelectedIndexLimits


async def expire_selected_metadata(
    session: AsyncSession,
    now: datetime,
    *,
    after: int | None = None,
    through: int | None = None,
    limit: int = 100,
) -> tuple[int | None, int | None, int]:
    """Caller commits; return next position, rotation high-water mark and erased rows.

    Scan at most limit rows by primary key, then remove eligible ones. Loss summaries
    and at most limit correction links are updated under the same gate. If a legacy
    parent has more references, retain it until a later rotation drains them.
    """
    if not 1 <= limit <= 100:
        raise ValueError("Selected metadata expiry batch must be 1 to 100")
    await SqlUserRepository(session).lock_administration()
    gate = await session.scalar(
        update(SelectedIndexGateRow)
        .where(SelectedIndexGateRow.id == 1)
        .values(revision=SelectedIndexGateRow.revision + 1)
        .returning(SelectedIndexGateRow.id)
    )
    if gate != 1:
        raise Conflict("Selected-index write gate is unavailable")
    if through is None:
        through = await session.scalar(select(func.max(SelectedIndexRecordRow.id)))
    if through is None:
        return None, None, 0
    # Freeze each rotation's end so continuing acquisition cannot postpone revisiting
    # older rows indefinitely. The primary-key maximum does not scan row contents.
    query = (
        select(SelectedIndexRecordRow)
        .where(SelectedIndexRecordRow.id <= through)
        .order_by(SelectedIndexRecordRow.id)
        .limit(limit)
    )
    if after is not None:
        query = query.where(SelectedIndexRecordRow.id > after)
    scanned = list(await session.scalars(query))
    cursor = scanned[-1].id if len(scanned) == limit and scanned[-1].id < through else None
    next_through = through if cursor is not None else None
    cutoff = now - timedelta(days=SelectedIndexLimits().max_age_days)
    expired = [row for row in scanned if row.expires_at <= now or row.first_seen_at <= cutoff]
    if not expired:
        return cursor, next_through, 0
    identifiers = [row.id for row in expired]
    references = list(
        await session.scalars(
            select(SelectedIndexRecordRow.id)
            .where(SelectedIndexRecordRow.corrects_id.in_(identifiers))
            .order_by(SelectedIndexRecordRow.id)
            .limit(limit)
        )
    )
    if references:
        await session.execute(
            update(SelectedIndexRecordRow)
            .where(SelectedIndexRecordRow.id.in_(references))
            .values(corrects_id=None)
            .execution_options(synchronize_session=False)
        )
    blocked = set(
        await session.scalars(
            select(SelectedIndexRecordRow.corrects_id)
            .where(SelectedIndexRecordRow.corrects_id.in_(identifiers))
            .distinct()
        )
    )
    removed = [row for row in expired if row.id not in blocked]
    for row in removed:
        await session.delete(row)
    await record_removed_rows(session, removed, "age", now)
    return cursor, next_through, len(removed)
