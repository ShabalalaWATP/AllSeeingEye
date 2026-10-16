"""Alert expiry removes delivery metadata on both production database backends."""

from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import delete, select, text

from alert_routing_helpers import delivery_store, enable_mail, fire, outbox, rule, save_route
from ase.adapters.persistence import alert_feedback
from ase.adapters.persistence.alert_notification_enqueue import enqueue_alert_notifications
from ase.adapters.persistence.alert_routing_models import AlertNotificationRow
from ase.adapters.persistence.models import AlertRow
from ase.adapters.persistence.warning_mapping import _alert_row
from ase.adapters.persistence.warning_store import SqlWarningStore
from ase.domain.notification_delivery import DeliveryOutcome
from ase.domain.warning import Alert

STATES = ("pending", "sending", "sent", "failed", "unavailable", "cancelled", "uncertain")


async def seed(container, fired_at, *, state="pending", owner=None):
    alert = Alert(uuid4(), uuid4(), fired_at, "Synthetic alert", "", 1, 1, (), (), created_by=owner)
    delivery = AlertNotificationRow(
        id=uuid4(),
        alert_id=alert.id,
        channel="email",
        destination_ref=str(uuid4()),
        route_revision=3,
        state=state,
        attempts=1,
        lease_token=uuid4() if state == "sending" else None,
        next_attempt_at=container.clock.now() + timedelta(minutes=15),
        safe_reason=None,
        created_at=fired_at,
        updated_at=container.clock.now(),
    )
    async with container.session_factory() as session:
        session.add(_alert_row(alert))
        await session.flush()
        session.add(delivery)
        await session.commit()
    return alert, delivery


async def snapshot(container):
    async with container.session_factory() as session:
        alerts = set(await session.scalars(select(AlertRow.id)))
        deliveries = {
            row.id: (
                row.state,
                row.attempts,
                row.lease_token,
                row.next_attempt_at,
                row.destination_ref,
            )
            for row in await session.scalars(select(AlertNotificationRow))
        }
        return alerts, deliveries


@pytest.mark.parametrize("state", STATES)
@pytest.mark.parametrize("enforce_sqlite_fks", [False, True])
async def test_expired_alert_prunes_outbox_and_preserves_live_boundary(
    container, state, enforce_sqlite_fks
):
    # Container constructs the engine/session factory used by the application.
    async with container.session_factory() as session:
        if session.get_bind().dialect.name == "sqlite":
            assert await session.scalar(text("PRAGMA foreign_keys")) == 0
            if enforce_sqlite_fks:
                await session.execute(text("PRAGMA foreign_keys = ON"))
                assert await session.scalar(text("PRAGMA foreign_keys")) == 1
        elif enforce_sqlite_fks:
            pytest.skip("PostgreSQL always enforces foreign keys; the default case covers it")
    cutoff = container.clock.now() - timedelta(days=30)
    expired, removed = await seed(container, cutoff - timedelta(microseconds=1), state=state)
    boundary, retained = await seed(container, cutoff, state=state, owner=uuid4())
    current, latest = await seed(container, container.clock.now(), state="pending", owner=uuid4())
    _, before = await snapshot(container)
    store = SqlWarningStore(container.session_factory, container.access_policy)

    assert await store.prune(cutoff) == 1
    alerts, deliveries = await snapshot(container)
    assert alerts == {boundary.id, current.id} and expired.id not in alerts
    assert removed.id not in deliveries
    assert deliveries == {retained.id: before[retained.id], latest.id: before[latest.id]}
    assert await store.prune(cutoff) == 0
    assert await snapshot(container) == (alerts, deliveries)


async def test_legacy_orphan_is_removed_even_when_no_alert_expires(container):
    if container.engine.dialect.name != "sqlite":
        pytest.skip("PostgreSQL already prevents this legacy orphan through its foreign key")
    cutoff = container.clock.now() - timedelta(days=30)
    orphan, removed = await seed(container, cutoff - timedelta(days=1), state="sending")
    current, retained = await seed(container, container.clock.now(), state="sent")
    async with container.session_factory() as session:
        await session.execute(delete(AlertRow).where(AlertRow.id == orphan.id))
        await session.commit()
    _, before = await snapshot(container)
    assert removed.id in before
    store = SqlWarningStore(container.session_factory, container.access_policy)

    assert await store.prune(cutoff) == 0
    assert await snapshot(container) == ({current.id}, {retained.id: before[retained.id]})


async def test_cleanup_failure_rolls_back_alerts_and_deliveries(container, monkeypatch):
    cutoff = container.clock.now() - timedelta(days=30)
    await seed(container, cutoff - timedelta(days=1))
    before = await snapshot(container)
    original = alert_feedback.prune

    async def fail(*args):
        raise RuntimeError("Synthetic later cleanup failure")

    monkeypatch.setattr(alert_feedback, "prune", fail)
    store = SqlWarningStore(container.session_factory, container.access_policy)
    with pytest.raises(RuntimeError, match="Synthetic later cleanup failure"):
        await store.prune(cutoff)
    assert await snapshot(container) == before
    monkeypatch.setattr(alert_feedback, "prune", original)
    assert await store.prune(cutoff) == 1
    assert await snapshot(container) == (set(), {})


@pytest.mark.parametrize("expired", [False, True])
async def test_claim_completion_and_retry_cannot_restore_pruned_rows(
    client, container, user, expired
):
    headers, identifier = await rule(client, user)
    await enable_mail(container, user)
    await save_route(client, headers, identifier)
    alert = await fire(container, identifier)
    delivery = delivery_store(container)
    claim = await delivery.claim(container.clock.now())
    assert claim is not None
    cutoff = container.clock.now() - timedelta(days=30)
    async with container.session_factory() as session:
        if expired:
            row = await session.get(AlertRow, alert.id)
            row.fired_at = cutoff - timedelta(microseconds=1)
        await session.commit()
    store = SqlWarningStore(container.session_factory, container.access_policy)
    assert await store.prune(cutoff) == int(expired)

    prepared = await delivery.prepare(claim, container.clock.now())
    await delivery.finish(claim, DeliveryOutcome.RETRYABLE, container.clock.now())
    if expired:
        assert prepared is None
        assert await outbox(container) == []
        assert await delivery.claim(container.clock.now() + timedelta(minutes=5)) is None
    else:
        assert prepared is not None
        container.clock.advance(timedelta(minutes=5))
        retry = await delivery.claim(container.clock.now())
        assert retry is not None and retry.id == claim.id and retry.attempts == 2
        assert await delivery.prepare(retry, container.clock.now()) is not None
        await delivery.finish(retry, DeliveryOutcome.SENT, container.clock.now())
        async with container.session_factory() as session:
            await enqueue_alert_notifications(session, alert, installation_copy=False)
            await session.commit()
        rows = await outbox(container)
        assert len(rows) == 1 and rows[0].id == claim.id and rows[0].state == "sent"
