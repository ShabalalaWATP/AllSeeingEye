"""Atomic warning consumption and bounded expiry, under the administration guard."""

import logging
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.warning_consumption_models import WarningConsumptionRow
from ase.application.feeds.cooperative_work import joined_thread_call
from ase.domain.consumed_evidence import (
    CONSUMED_RETENTION,
    EPOCH,
    MAX_CONSUMED_PER_RULE,
    MAX_CONSUMED_TOTAL,
    MAX_INSTANT,
    RETENTION_MICROSECONDS,
    ConsumedEvidence,
    Identity,
    active,
    decode,
    encode,
    instant,
)

log = logging.getLogger(__name__)


def warn(indicator_id: UUID, reason: str) -> None:
    log.warning(
        "indicator_evidence_deferred",
        extra={"indicator_id": str(indicator_id), "reason": reason},
    )


async def load(session: AsyncSession, identifier: UUID, now: datetime) -> ConsumedEvidence:
    row = await session.get(WarningConsumptionRow, identifier)
    if row is None:
        return ConsumedEvidence()
    try:
        entries = await _entries(row, now)
    except ValueError:
        return ConsumedEvidence(unavailable="invalid_consumed_evidence")
    legacy = row.legacy_before
    if legacy is not None and legacy < now - CONSUMED_RETENTION:
        legacy = None
    return ConsumedEvidence(frozenset(entries), legacy)


async def _entries(row: WarningConsumptionRow, now: datetime) -> dict[bytes, int]:
    data, count = row.data, row.count
    return await joined_thread_call(lambda: active(decode(data, count), now))


async def _fill(row: WarningConsumptionRow, entries: dict[bytes, int]) -> None:
    packed, expiry = await joined_thread_call(
        lambda: (encode(entries), min(entries.values()) if entries else None)
    )
    row.data, row.count = packed, len(entries)
    row.expires_at = EPOCH + timedelta(microseconds=expiry) if expiry is not None else None


async def prune(session: AsyncSession, now: datetime) -> None:
    rows = await session.scalars(
        select(WarningConsumptionRow).where(
            or_(
                WarningConsumptionRow.expires_at < now,
                WarningConsumptionRow.legacy_before < now - CONSUMED_RETENTION,
            )
        )
    )
    for row in rows:
        try:
            entries = await _entries(row, now)
        except ValueError:
            warn(row.indicator_id, "invalid_consumed_evidence")
            continue  # Never turn corrupt state into empty state and replay its evidence.
        if row.legacy_before is not None and row.legacy_before < now - CONSUMED_RETENTION:
            row.legacy_before = None
        if not entries and row.legacy_before is None:
            await session.delete(row)
        else:
            await _fill(row, entries)
    await session.flush()


async def consume(
    session: AsyncSession,
    identifier: UUID,
    incoming: tuple[Identity, ...] | None,
    now: datetime,
) -> bool:
    """Called inside the same guarded transaction as the alert and notifications.

    The sum and the row update share the cross-process administration lock. Capacity
    failure rejects the entire firing. No still-eligible identity is evicted.
    """
    await prune(session, now)
    row = await session.get(WarningConsumptionRow, identifier)
    try:
        entries = {} if row is None else await _entries(row, now)
    except ValueError:
        warn(identifier, "invalid_consumed_evidence")
        return False
    if incoming is None:
        # Compatibility for callers without a complete evaluation snapshot. These
        # alerts cannot prove which uncited matches were consumed.
        if row is None:
            row = WarningConsumptionRow(indicator_id=identifier)
            session.add(row)
        row.legacy_before = max(row.legacy_before or now, now)
        await _fill(row, entries)
        return True
    if len(incoming) > MAX_CONSUMED_PER_RULE:
        warn(identifier, "rule_consumed_evidence_capacity")
        return False
    added = dict(incoming)
    oldest = instant(now)
    newest = min(MAX_INSTANT, oldest + RETENTION_MICROSECONDS)
    if (
        not incoming
        or len(added) != len(incoming)
        or any(len(key) != 16 or not oldest <= expiry <= newest for key, expiry in incoming)
        or any(key in entries for key in added)
    ):
        warn(identifier, "stale_or_invalid_consumption")
        return False
    total = int(
        await session.scalar(select(func.coalesce(func.sum(WarningConsumptionRow.count), 0))) or 0
    )
    reason = (
        "rule_consumed_evidence_capacity"
        if len(entries) + len(added) > MAX_CONSUMED_PER_RULE
        else "global_consumed_evidence_capacity"
        if total + len(added) > MAX_CONSUMED_TOTAL
        else None
    )
    if reason:
        warn(identifier, reason)
        return False
    entries.update(added)
    if row is None:
        row = WarningConsumptionRow(indicator_id=identifier)
        session.add(row)
    await _fill(row, entries)
    return True
