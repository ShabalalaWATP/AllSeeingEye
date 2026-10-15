"""Strict boundaries, category holds, bounded transactions and minimal durable receipts."""

from datetime import timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.models import AuditLogRow, LlmUsageRow
from ase.adapters.persistence.notification_digest_models import DigestDeliveryRow
from ase.adapters.persistence.subscription_edition_models import SubscriptionDeliveryRow
from operational_retention_helpers import audit, count, digest, email, run, seed, usage
from test_notification_delivery import setup_delivery


@pytest.mark.parametrize("offset", [-1, 0, 1])
async def test_exact_boundaries(container, user, offset):
    _, edition, _ = await setup_delivery(container, user)
    initial_audits = await count(container, AuditLogRow)
    now = container.clock.now()
    delta = timedelta(microseconds=offset)
    await seed(
        container,
        audit(now - timedelta(days=365) + delta),
        usage(now - timedelta(days=400) + delta),
        email(edition, user, now - timedelta(days=90) + delta),
        digest(user, now - timedelta(days=90) + delta),
    )
    expected = int(offset < 0)
    assert (await run(container, dry_run=True)) == dict.fromkeys(
        ("audit", "llm_usage", "subscription_email", "digest"), expected
    )
    assert await count(container, AuditLogRow) == initial_audits + 1
    assert (await run(container))["audit"] == expected
    assert await count(container, AuditLogRow) == initial_audits + 1 - expected
    assert await count(container, LlmUsageRow) == 1 - expected
    async with container.session_factory() as session:
        row = await session.scalar(select(SubscriptionDeliveryRow))
        assert (row.destination_ref is None) == bool(expected)
        assert row.updated_at == now - timedelta(days=90) + delta
        row = await session.scalar(select(DigestDeliveryRow))
        assert (row.safe_reason is None) == bool(expected)
        assert row.timezone == "Pacific/Kiritimati"


@pytest.mark.parametrize(
    "state",
    [
        "sent",
        "failed",
        "cancelled",
        "uncertain",
        "empty",
        "pending",
        "sending",
        "unavailable",
        "unknown",
    ],
)
async def test_only_terminal_delivery_metadata_is_minimised(container, user, state):
    _, edition, _ = await setup_delivery(container, user)
    at = container.clock.now() - timedelta(days=100)
    mail, daily = email(edition, user, at, state=state), digest(user, at, state=state)
    in_app = email(edition, user, at, state=state, channel="in_app")
    await seed(container, mail, daily, in_app)
    result = await run(container)
    assert result["subscription_email"] == int(
        state in {"sent", "failed", "cancelled", "uncertain"}
    )
    assert result["digest"] == int(state in {"sent", "failed", "cancelled", "uncertain", "empty"})
    async with container.session_factory() as session:
        for before in (mail, daily, in_app):
            after = await session.get(type(before), before.id)
            for field in ("id", "state", "attempts", "created_at", "updated_at"):
                assert getattr(after, field) == getattr(before, field)
        after = await session.get(SubscriptionDeliveryRow, mail.id)
        assert after.idempotency_key == mail.idempotency_key
        assert after.edition_id == edition.id and after.event_kind == "attention"
        after = await session.get(SubscriptionDeliveryRow, in_app.id)
        assert after.destination_ref == user.id and after.safe_reason == in_app.safe_reason
        after = await session.get(DigestDeliveryRow, daily.id)
        assert (
            after.user_id,
            after.local_day,
            after.timezone,
            after.window_start,
            after.window_end,
        ) == (daily.user_id, daily.local_day, daily.timezone, daily.window_start, daily.window_end)
    assert not any((await run(container)).values())


@pytest.mark.parametrize("hold", ["audit", "llm_usage", "subscription_email", "digest", "all"])
async def test_holds_preserve_records_and_preview_matches_apply(container, user, hold):
    _, edition, _ = await setup_delivery(container, user)
    at = container.clock.now() - timedelta(days=500)
    await seed(container, audit(at), usage(at), email(edition, user, at), digest(user, at))
    policy = {"paused": True} if hold == "all" else {"held_categories": frozenset({hold})}
    preview = await run(container, dry_run=True, **policy)
    assert await run(container, **policy) == preview
    if hold == "all":
        assert preview == {}
    else:
        assert preview[hold] == 0 and sum(preview.values()) == 3
    result = await run(container)
    assert sum(result.values()) == (4 if hold == "all" else 1)


async def test_large_backlog_progresses_without_revisiting_minimised_rows(container, user):
    _, edition, _ = await setup_delivery(container, user)
    initial_audits = await count(container, AuditLogRow)
    at = container.clock.now() - timedelta(days=500)
    for index in range(205):
        await seed(
            container,
            audit(at),
            usage(at),
            email(edition, user, at),
            digest(user, at, day=(at - timedelta(days=index)).date().isoformat()),
        )
    for expected in (100, 100, 5, 0):
        result = await run(container)
        assert set(result.values()) == {expected}
    assert await count(container, AuditLogRow) == initial_audits
    assert await count(container, LlmUsageRow) == 0
    assert (
        await count(container, SubscriptionDeliveryRow)
        == await count(container, DigestDeliveryRow)
        == 205
    )


async def test_failed_commit_rolls_back_all_categories(container, user, monkeypatch):
    _, edition, _ = await setup_delivery(container, user)
    initial_audits = await count(container, AuditLogRow)
    at = container.clock.now() - timedelta(days=500)
    mail, daily = email(edition, user, at), digest(user, at)
    await seed(container, audit(at), usage(at), mail, daily)
    original = AsyncSession.commit

    async def fail(_session):
        raise RuntimeError("injected commit failure")

    monkeypatch.setattr(AsyncSession, "commit", fail)
    with pytest.raises(RuntimeError, match="injected"):
        await run(container)
    assert await count(container, AuditLogRow) == initial_audits + 1
    assert await count(container, LlmUsageRow) == 1
    async with container.session_factory() as session:
        assert (await session.get(SubscriptionDeliveryRow, mail.id)).destination_ref == user.id
        assert (await session.get(DigestDeliveryRow, daily.id)).safe_reason == daily.safe_reason
    monkeypatch.setattr(AsyncSession, "commit", original)
    assert sum((await run(container)).values()) == 4


async def test_integer_history_can_append_after_complete_purge(container):
    at = container.clock.now() - timedelta(days=500)
    await seed(container, audit(at), usage(at))
    assert sum((await run(container)).values()) == 2
    assert await count(container, AuditLogRow) == await count(container, LlmUsageRow) == 0
    # SQLite may reuse an ID. Holds intentionally cover categories, not reusable IDs.
    await seed(container, audit(container.clock.now()), usage(container.clock.now()))
    assert await count(container, AuditLogRow) == await count(container, LlmUsageRow) == 1
