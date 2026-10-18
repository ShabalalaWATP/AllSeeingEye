"""Dormant alert, push and research histories obey existing windows and batch limits."""

from datetime import timedelta
from uuid import uuid4

from sqlalchemy import func, select

from ase.adapters.persistence.alert_feedback import AlertFeedbackRow
from ase.adapters.persistence.alert_routing_models import AlertNotificationRow
from ase.adapters.persistence.dormant_retention import (
    prune_alert_history,
    prune_push_receipts,
    prune_research_counters,
)
from ase.adapters.persistence.operational_models import AlertRow
from ase.adapters.persistence.research_usage_models import ResearchTierRow, ResearchUsageRow
from ase.adapters.persistence.web_push_models import PushDeliveryRow, PushDeviceRow
from ase.domain.research_usage import period_bounds
from dormant_retention_helpers import seed


def alert(now, **values):
    return AlertRow(
        **(
            {
                "id": uuid4(),
                "indicator_id": uuid4(),
                "fired_at": now,
                "title": "Synthetic alert",
                "count": 1,
                "threshold": 1,
            }
            | values
        )
    )


def notification(identifier, now, number):
    return AlertNotificationRow(
        id=uuid4(),
        alert_id=identifier,
        channel="email",
        destination_ref=str(number),
        route_revision=1,
        state="pending",
        attempts=2,
        next_attempt_at=now,
        created_at=now,
        updated_at=now,
    )


async def test_alert_children_drain_before_parents_and_live_retry_receipts_survive(container):
    now = container.clock.now()
    old = alert(now - timedelta(days=30, microseconds=1))
    boundary = alert(now - timedelta(days=30))
    await seed(container, old, boundary)
    await seed(
        container,
        *[notification(old.id, now, i) for i in range(205)],
        notification(boundary.id, now - timedelta(days=31), 999),
    )
    for removed_children, removed_parents in [(100, 0), (100, 0), (5, 1)]:
        async with container.session_factory() as session:
            counts = await prune_alert_history(session, now)
            assert counts["alert_notifications"] == removed_children
            assert counts["alerts"] == removed_parents
            await session.commit()
    async with container.session_factory() as session:
        retained = await session.scalar(select(AlertNotificationRow))
        assert (retained.alert_id, retained.state, retained.attempts) == (boundary.id, "pending", 2)
        assert list(await session.scalars(select(AlertRow.id))) == [boundary.id]


async def test_alert_feedback_and_parent_backlogs_are_bounded_and_rollback_atomic(container):
    now = container.clock.now()
    day = (now - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
    await seed(
        container,
        *[alert(now - timedelta(days=31)) for _ in range(105)],
        *[
            AlertFeedbackRow(indicator_id=uuid4(), day=day, disposition="noise", count=1)
            for _ in range(105)
        ],
        AlertFeedbackRow(
            indicator_id=uuid4(), day=day + timedelta(days=1), disposition="useful", count=1
        ),
    )
    async with container.session_factory() as session:
        assert await prune_alert_history(session, now) == {
            "alert_notifications": 0,
            "alerts": 100,
            "alert_feedback": 100,
        }
        await session.rollback()
    async with container.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(AlertRow)) == 105
        assert (await prune_alert_history(session, now))["alerts"] == 100
        await session.commit()
    async with container.session_factory() as session:
        assert await prune_alert_history(session, now) == {
            "alert_notifications": 0,
            "alerts": 5,
            "alert_feedback": 5,
        }
        await session.commit()
        assert (await session.scalar(select(AlertFeedbackRow))).disposition == "useful"


async def test_push_cleanup_preserves_devices_current_leases_and_recent_alert_dedup(
    container, user
):
    now = container.clock.now()
    device = PushDeviceRow(
        id=uuid4(),
        user_id=user.id,
        family_id=uuid4(),
        security_version=0,
        endpoint_hash="a" * 64,
        encrypted_subscription="synthetic",
        created_at=now,
        next_check_at=now,
    )
    recent = alert(now - timedelta(days=1))
    await seed(container, device, recent)
    kept = set()
    rows = []
    for state, age, updated, alert_id, keep in [
        ("sent", timedelta(days=7), now, uuid4(), True),
        ("sending", timedelta(days=8), now - timedelta(minutes=1), uuid4(), True),
        ("sent", timedelta(days=8), now, recent.id, True),
        ("sending", timedelta(days=8), now - timedelta(minutes=1, microseconds=1), uuid4(), False),
        ("pending", timedelta(days=8), now, uuid4(), False),
        ("uncertain", timedelta(days=8), now, uuid4(), False),
    ]:
        identifier = uuid4()
        rows.append(
            PushDeliveryRow(
                id=identifier,
                device_id=device.id,
                alert_id=alert_id,
                state=state,
                lease_token=uuid4(),
                created_at=now - age,
                updated_at=updated,
            )
        )
        if keep:
            kept.add(identifier)
    await seed(container, *rows)
    async with container.session_factory() as session:
        assert await prune_push_receipts(session, now) == 3
        await session.commit()
        assert set(await session.scalars(select(PushDeliveryRow.id))) == kept
        assert await session.get(PushDeviceRow, device.id) is not None


async def test_old_research_buckets_drain_without_resetting_current_allowance_or_tier(
    container, user
):
    now = container.clock.now()
    day, _ = period_bounds(now, "day")
    week, _ = period_bounds(now, "week")
    await seed(
        container,
        ResearchTierRow(user_id=user.id, tier=3, revision=7),
        *[
            ResearchUsageRow(
                user_id=user.id, period="day", period_start=day - timedelta(days=i), used=9
            )
            for i in range(1, 106)
        ],
        ResearchUsageRow(
            user_id=user.id, period="week", period_start=week - timedelta(days=7), used=5
        ),
        ResearchUsageRow(user_id=user.id, period="day", period_start=day, used=4),
        ResearchUsageRow(user_id=user.id, period="week", period_start=week, used=8),
        ResearchUsageRow(
            user_id=user.id, period="day", period_start=day + timedelta(days=1), used=1
        ),
    )
    async with container.session_factory() as session:
        assert await prune_research_counters(session, now) == 100
        await session.commit()
        assert await prune_research_counters(session, now) == 6
        await session.commit()
        assert await prune_research_counters(session, now) == 0
        rows = list(await session.scalars(select(ResearchUsageRow)))
        assert {(r.period, r.period_start, r.used) for r in rows} == {
            ("day", day, 4),
            ("week", week, 8),
            ("day", day + timedelta(days=1), 1),
        }
        tier = await session.get(ResearchTierRow, user.id)
        assert (tier.tier, tier.revision) == (3, 7)
