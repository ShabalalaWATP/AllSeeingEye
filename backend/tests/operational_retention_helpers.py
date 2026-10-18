"""Synthetic history records and bounded maintenance test operations."""

from datetime import timedelta
from uuid import uuid4

from sqlalchemy import func, select

from ase.adapters.persistence.models import AuditLogRow, LlmUsageRow
from ase.adapters.persistence.notification_digest_models import DigestDeliveryRow
from ase.adapters.persistence.subscription_edition_models import SubscriptionDeliveryRow
from ase.container.operational_retention import maintain_operations
from ase.domain.operational_retention import OperationalRetentionPolicy


def audit(at):
    return AuditLogRow(
        at=at,
        action="login",
        subject="synthetic@example.invalid",
        ip="192.0.2.1",
        details={"title": "Synthetic retained title"},
    )


def usage(at, *, owner=None, tokens=123):
    return LlmUsageRow(
        at=at,
        profile_id=uuid4(),
        user_id=owner,
        purpose="report-job",
        ok=True,
        latency_ms=10,
        prompt_tokens=99,
        completion_tokens=tokens,
        error="synthetic provider detail",
    )


def email(edition, user, at, *, state="sent", channel="email"):
    return SubscriptionDeliveryRow(
        id=uuid4(),
        edition_id=edition.id,
        channel=channel,
        destination_ref=user.id,
        event_kind="attention",
        idempotency_key=uuid4(),
        state=state,
        attempts=2,
        created_at=at - timedelta(days=1),
        updated_at=at,
        lease_token=uuid4(),
        next_attempt_at=at + timedelta(minutes=5),
        safe_reason="acceptance_unknown",
    )


def digest(user, at, *, state="sent", day=None):
    return DigestDeliveryRow(
        id=uuid4(),
        user_id=user.id,
        local_day=day or at.date().isoformat(),
        timezone="Pacific/Kiritimati",
        window_start=at - timedelta(days=1),
        window_end=at,
        state=state,
        attempts=2,
        created_at=at,
        updated_at=at,
        lease_token=uuid4(),
        next_attempt_at=at + timedelta(minutes=5),
        safe_reason="acceptance_unknown",
    )


async def seed(container, *rows):
    async with container.session_factory() as session:
        session.add_all(rows)
        await session.commit()


async def count(container, model):
    async with container.session_factory() as session:
        return await session.scalar(select(func.count()).select_from(model))


async def run(container, *, dry_run=False, **policy):
    return await maintain_operations(
        container.session_factory,
        container.clock.now(),
        OperationalRetentionPolicy(**policy),
        dry_run=dry_run,
    )
