"""Atomic first acknowledgements and small scoped daily disposition counters."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, Integer, String, Uuid, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base, UTCDateTime
from ase.adapters.persistence.operational_models import AlertRow
from ase.domain.alert_feedback import AlertDisposition
from ase.domain.warning import Alert


class AlertFeedbackRow(Base):
    __tablename__ = "alert_feedback_days"
    __table_args__ = (
        CheckConstraint("count >= 1", name="ck_alert_feedback_count"),
        CheckConstraint(
            "disposition IN ('useful', 'noise', 'duplicate')", name="ck_alert_feedback_disposition"
        ),
    )
    indicator_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    day: Mapped[datetime] = mapped_column(UTCDateTime, primary_key=True, index=True)
    disposition: Mapped[str] = mapped_column(String(12), primary_key=True)
    created_by: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    team_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    count: Mapped[int] = mapped_column(Integer)


async def acknowledge(session: AsyncSession, alert: Alert) -> bool:
    """CAS plus bucket increment is one transaction, guarded by administration admission."""
    result = await session.execute(
        update(AlertRow)
        .where(AlertRow.id == alert.id, AlertRow.acknowledged_at.is_(None))
        .values(
            acknowledged_at=alert.acknowledged_at,
            acknowledged_by=alert.acknowledged_by,
            disposition=alert.disposition,
            disposition_note=alert.disposition_note,
        )
    )
    if result.rowcount != 1:  # type: ignore[attr-defined]
        return False
    if alert.indicator_id is None or alert.disposition is None or alert.acknowledged_at is None:
        return True
    day = alert.acknowledged_at.replace(hour=0, minute=0, second=0, microsecond=0)
    key = (alert.indicator_id, day, alert.disposition.value)
    bucket = await session.get(AlertFeedbackRow, key)
    if bucket is None:
        session.add(
            AlertFeedbackRow(
                indicator_id=alert.indicator_id,
                day=day,
                disposition=alert.disposition.value,
                created_by=alert.created_by,
                team_id=alert.team_id,
                count=1,
            )
        )
    else:
        bucket.count += 1
    await session.flush()
    return True


async def counts(
    session: AsyncSession,
    indicator_id: UUID,
    created_by: UUID,
    team_id: UUID | None,
    since: datetime,
    until: datetime,
) -> dict[AlertDisposition, int]:
    rows = await session.execute(
        select(AlertFeedbackRow.disposition, func.sum(AlertFeedbackRow.count))
        .where(
            AlertFeedbackRow.indicator_id == indicator_id,
            AlertFeedbackRow.created_by == created_by,
            AlertFeedbackRow.team_id == team_id,
            AlertFeedbackRow.day >= since,
            AlertFeedbackRow.day < until,
        )
        .group_by(AlertFeedbackRow.disposition)
    )
    return {AlertDisposition(disposition): int(count) for disposition, count in rows}


async def prune(session: AsyncSession, before: datetime) -> None:
    await session.execute(delete(AlertFeedbackRow).where(AlertFeedbackRow.day < before))
