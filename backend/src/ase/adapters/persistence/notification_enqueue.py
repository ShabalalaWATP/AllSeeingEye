"""Commit-free edition intents share the publication or attention transition transaction."""

from datetime import datetime
from uuid import UUID, uuid5

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.notification_models import SubscriptionNotificationRow
from ase.adapters.persistence.subscription_edition_models import SubscriptionDeliveryRow
from ase.domain.subscription_editions import SubscriptionEdition

NAMESPACE = UUID("cf826ba5-7b1c-4753-a5c4-491271196af7")


async def queue_attention_transition(
    session: AsyncSession,
    previous: SubscriptionEdition,
    current: SubscriptionEdition,
) -> None:
    attention = (
        previous.workflow != current.workflow
        and current.workflow.value in {"failed", "blocked", "paused"}
    ) or (
        previous.report_quality != current.report_quality
        and current.report_quality.value in {"needs_review", "failed"}
    )
    if attention:
        await queue_edition_notifications(session, current, current.updated_at, "attention")


async def queue_edition_notifications(
    session: AsyncSession,
    edition: SubscriptionEdition,
    now: datetime,
    event_kind: str,
) -> None:
    """Unique database keys make retries harmless, including already-sent intents."""
    if event_kind not in {"edition_available", "material_change", "attention"}:
        raise ValueError("Unknown edition notification event.")
    predicate = (
        SubscriptionNotificationRow.attention.is_(True)
        if event_kind == "attention"
        else SubscriptionNotificationRow.email_policy
        == ("every_edition" if event_kind == "edition_available" else "material_changes")
    )
    # Opt-ins are capped at 100 per subscription by the management path. No report
    # fields, recipient addresses or names are copied into the durable intent.
    recipients = await session.scalars(
        select(SubscriptionNotificationRow.user_id)
        .where(
            SubscriptionNotificationRow.subscription_id == edition.subscription_id,
            predicate,
        )
        .limit(100)
    )
    insert = sqlite_insert if session.get_bind().dialect.name == "sqlite" else pg_insert
    for recipient in recipients:
        key = uuid5(NAMESPACE, f"{edition.id}:{event_kind}:{recipient}")
        await session.execute(
            insert(SubscriptionDeliveryRow)
            .values(
                id=key,
                edition_id=edition.id,
                channel="email",
                destination_ref=recipient,
                event_kind=event_kind,
                idempotency_key=key,
                state="pending",
                attempts=0,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_nothing()
        )
