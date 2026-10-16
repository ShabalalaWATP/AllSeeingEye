"""Minimised receipts must not revive deliveries or change monthly admission."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from ase.adapters.persistence.monthly_report_usage import monthly_usage, require_admission_room
from ase.adapters.persistence.notification_digest_models import (
    DigestDeliveryRow,
    DigestPreferenceRow,
)
from ase.adapters.persistence.notification_digest_schedule import SqlDigestScheduler
from ase.adapters.persistence.notification_preferences import SqlNotificationPreferences
from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.adapters.persistence.subscription_edition_models import SubscriptionDeliveryRow
from ase.application.report_jobs.budget import JobInterrupted
from ase.container.notifications import digest_preferences, digest_worker
from ase.domain.notification_delivery import DeliveryOutcome, EmailPreferences
from ase.domain.notification_digest import DigestPreferences
from ase.domain.subscription_monthly_budget import (
    MonthlyBudgetExhausted,
    MonthlyBudgetPolicy,
    MonthlyLimit,
)
from operational_retention_helpers import count, run, seed, usage
from report_job_helpers import job
from test_notification_delivery import _enqueue, setup_delivery
from test_notification_digest import _enable


@pytest.mark.parametrize("outcome", [DeliveryOutcome.SENT, DeliveryOutcome.UNCERTAIN])
@pytest.mark.parametrize("event", ["edition_available", "attention"])
async def test_compaction_keeps_idempotency_and_fences_late_completion(
    container, user, outcome, event
):
    _, edition, store = await setup_delivery(container, user)
    await _enqueue(container, edition, event)
    claim = await store.claim(container.clock.now())
    assert claim is not None
    await store.finish(claim, outcome, container.clock.now())
    container.clock.advance(timedelta(days=91))
    assert (await run(container))["subscription_email"] == 1
    await _enqueue(container, edition, event)
    await store.finish(claim, DeliveryOutcome.RETRYABLE, container.clock.now())
    assert await store.claim(container.clock.now()) is None
    assert await count(container, SubscriptionDeliveryRow) == 1
    async with container.session_factory() as session:
        row = await session.get(SubscriptionDeliveryRow, claim.id)
        assert row.state == outcome.value and row.destination_ref is None


@pytest.mark.parametrize("claimed", [False, True])
async def test_opt_out_after_long_inactivity_then_opt_in_does_not_revive_old_mail(
    container, user, claimed
):
    _, edition, store = await setup_delivery(container, user)
    await _enqueue(container, edition)
    if claimed:
        assert await store.claim(container.clock.now()) is not None
    container.clock.advance(timedelta(days=91))
    async with container.session_factory() as session:
        await SqlNotificationPreferences(session).save_email(user.id, EmailPreferences())
        await session.commit()
    # Retention measures recorded delivery inactivity, not the opt-out timestamp.
    assert (await run(container))["subscription_email"] == 1
    async with container.session_factory() as session:
        await SqlNotificationPreferences(session).save_email(user.id, EmailPreferences(True))
        await session.commit()
    await _enqueue(container, edition)
    assert await store.claim(container.clock.now()) is None
    async with container.session_factory() as session:
        row = await session.scalar(select(SubscriptionDeliveryRow))
        assert row.state == ("uncertain" if claimed else "cancelled")


async def test_retryable_history_survives_and_can_complete(container, user):
    _, edition, store = await setup_delivery(container, user)
    await _enqueue(container, edition)
    first = await store.claim(container.clock.now())
    await store.finish(first, DeliveryOutcome.UNAVAILABLE, container.clock.now())
    container.clock.advance(timedelta(days=91))
    assert (await run(container))["subscription_email"] == 0
    second = await store.claim(container.clock.now())
    assert second is not None and second.recipient_id == user.id
    assert await store.prepare(second, container.clock.now()) is not None
    await store.finish(second, DeliveryOutcome.SENT, container.clock.now())


async def test_digest_day_receipt_survives_compaction_and_schedule_changes(container, user):
    await _enable(container, user)
    container.clock.advance(timedelta(days=1))
    scheduler = SqlDigestScheduler(container.session_factory, container.access_policy)
    assert await scheduler.enqueue_due(container.clock.now()) == 1
    store = digest_worker(container)._dispatcher._store
    claim = await store.claim(container.clock.now())
    assert claim is not None
    assert await store.prepare(claim, container.clock.now()) is None  # empty daily window
    async with container.session_factory() as session:
        before = await session.get(DigestDeliveryRow, claim.id)
    container.clock.advance(timedelta(days=91))
    assert (await run(container))["digest"] == 1
    await store.finish(claim, DeliveryOutcome.RETRYABLE, container.clock.now())
    async with container.session_factory() as session:
        await digest_preferences(container, session).save(
            user, DigestPreferences(True, "Pacific/Kiritimati", 9)
        )
    # Simulate repeated scheduling of an already recorded day after clock correction.
    container.clock.advance(before.window_end - container.clock.now())
    async with container.session_factory() as session:
        preference = await session.get(DigestPreferenceRow, user.id)
        preference.timezone, preference.hour = "UTC", 8
        preference.cursor_at = before.window_start
        preference.next_due_at = before.window_end
        await session.commit()
    assert await scheduler.enqueue_due(container.clock.now()) == 0
    assert await count(container, DigestDeliveryRow) == 1
    assert await store.claim(container.clock.now()) is None
    async with container.session_factory() as session:
        after = await session.get(DigestDeliveryRow, claim.id)
        assert after.state == "empty" and after.safe_reason is None
        assert after.local_day == before.local_day and after.window_start == before.window_start


@pytest.mark.parametrize("invalid", [False, True])
async def test_current_month_accounting_and_fail_closed_receipts_survive_shortest_policy(
    container, user, invalid
):
    now = datetime(2026, 1, 31, 23, tzinfo=UTC)
    container.clock.advance(now - container.clock.now())
    await seed(
        container,
        usage(datetime(2026, 1, 1, tzinfo=UTC), owner=user.id, tokens=-1 if invalid else 123),
        usage(datetime(2025, 12, 31, tzinfo=UTC), owner=user.id),
    )
    policy = MonthlyBudgetPolicy(owner=MonthlyLimit(1, 1000))

    async def accounting():
        async with container.session_factory() as session:
            if invalid:
                with pytest.raises(JobInterrupted):
                    await monthly_usage(session, user.id, None, now)
            else:
                result, _ = await monthly_usage(session, user.id, None, now)
                assert result.requests == 1 and result.output_tokens == 123
                with pytest.raises(MonthlyBudgetExhausted):
                    await require_admission_room(session, user.id, None, now, policy)

    await accounting()
    assert (await run(container, usage_days=30))["llm_usage"] == 1
    await accounting()


async def test_uncertain_job_reservation_and_checkpoint_survive(container, user):
    now = container.clock.now()
    retained = job(
        owner_id=user.id,
        created_at=now,
        updated_at=now,
        status="paused",
        payload={
            "schema_version": 1,
            "calls": [
                {"status": "uncertain", "reserved_output": 100, "dispatched_at": now.isoformat()}
            ],
        },
    )
    async with container.session_factory() as session:
        await SqlReportJobRepository(session).add(retained)
        await session.commit()
    await seed(container, usage(now - timedelta(days=401), owner=user.id))
    assert (await run(container))["llm_usage"] == 1
    async with container.session_factory() as session:
        result, _ = await monthly_usage(session, user.id, None, now)
        assert result.requests == 1 and result.output_tokens == 100
        saved = await SqlReportJobRepository(session).get(retained.id)
        assert saved.payload == retained.payload
