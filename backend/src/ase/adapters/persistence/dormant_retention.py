"""Bounded expiry of established operational windows, without activating providers."""

from datetime import datetime, timedelta
from typing import Any, cast

from sqlalchemy import delete, exists, or_, select, tuple_
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.sql.elements import ColumnElement

from ase.adapters.persistence.alert_feedback import AlertFeedbackRow
from ase.adapters.persistence.alert_routing_models import AlertNotificationRow
from ase.adapters.persistence.base import Base
from ase.adapters.persistence.models import AlertRow
from ase.adapters.persistence.research_usage_models import ResearchUsageRow
from ase.adapters.persistence.users import SqlUserRepository
from ase.adapters.persistence.web_push_models import PushDeliveryRow
from ase.domain.research_usage import period_bounds
from ase.domain.warning import ALERT_RETENTION

BATCH = 100


async def _delete_batch(
    session: AsyncSession,
    model: type[Base],
    keys: tuple[InstrumentedAttribute[Any], ...],
    predicate: ColumnElement[bool],
    order: InstrumentedAttribute[Any],
) -> int:
    rows = (
        await session.execute(select(*keys).where(predicate).order_by(order, *keys).limit(BATCH))
    ).all()
    if not rows:
        return 0
    selected = (
        keys[0].in_([row[0] for row in rows])
        if len(keys) == 1
        else tuple_(*keys).in_([tuple(row) for row in rows])
    )
    result = await session.execute(
        delete(model).where(selected, predicate).execution_options(synchronize_session=False)
    )
    return int(cast("CursorResult[Any]", result).rowcount or 0)


async def prune_alert_history(session: AsyncSession, now: datetime) -> dict[str, int]:
    """Drain expired-alert children before parents, and repair legacy SQLite orphans."""
    await SqlUserRepository(session).lock_administration()
    cutoff = now - ALERT_RETENTION
    notifications = await _delete_batch(
        session,
        AlertNotificationRow,
        (AlertNotificationRow.id,),
        ~exists().where(AlertRow.id == AlertNotificationRow.alert_id)
        | exists().where(AlertRow.id == AlertNotificationRow.alert_id, AlertRow.fired_at < cutoff),
        AlertNotificationRow.created_at,
    )
    alerts = await _delete_batch(
        session,
        AlertRow,
        (AlertRow.id,),
        (AlertRow.fired_at < cutoff)
        & ~exists().where(AlertNotificationRow.alert_id == AlertRow.id),
        AlertRow.fired_at,
    )
    day = cutoff.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    feedback = await _delete_batch(
        session,
        AlertFeedbackRow,
        (AlertFeedbackRow.indicator_id, AlertFeedbackRow.day, AlertFeedbackRow.disposition),
        AlertFeedbackRow.day < day,
        AlertFeedbackRow.day,
    )
    return {"alert_notifications": notifications, "alerts": alerts, "alert_feedback": feedback}


async def prune_push_receipts(session: AsyncSession, now: datetime) -> int:
    """Preserve a current lease and the alert's one-day duplicate-prevention horizon."""
    return await _delete_batch(
        session,
        PushDeliveryRow,
        (PushDeliveryRow.id,),
        (PushDeliveryRow.created_at < now - timedelta(days=7))
        & or_(
            PushDeliveryRow.state != "sending",
            PushDeliveryRow.updated_at < now - timedelta(minutes=1),
        )
        & ~exists().where(
            AlertRow.id == PushDeliveryRow.alert_id, AlertRow.fired_at >= now - timedelta(days=1)
        ),
        PushDeliveryRow.created_at,
    )


async def prune_research_counters(session: AsyncSession, now: datetime) -> int:
    """Serialise with admission/tier changes; retain current and future calendar buckets."""
    await SqlUserRepository(session).lock_administration()
    day, _ = period_bounds(now, "day")
    week, _ = period_bounds(now, "week")
    predicate = or_(
        (ResearchUsageRow.period == "day") & (ResearchUsageRow.period_start < day),
        (ResearchUsageRow.period == "week") & (ResearchUsageRow.period_start < week),
    )
    keys = (ResearchUsageRow.user_id, ResearchUsageRow.period, ResearchUsageRow.period_start)
    selected = (
        await session.execute(select(*keys).where(predicate).order_by(*keys).limit(BATCH))
    ).all()
    if not selected:
        return 0
    for owner in sorted({row.user_id for row in selected}):
        await SqlUserRepository(session).lock_by_id(owner)
    result = await session.execute(
        delete(ResearchUsageRow)
        .where(tuple_(*keys).in_([tuple(row) for row in selected]), predicate)
        .execution_options(synchronize_session=False)
    )
    return int(cast("CursorResult[Any]", result).rowcount or 0)
