"""An explicit opt-out permanently fences existing subscription email intents."""

from uuid import UUID

from sqlalchemy import case, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.subscription_edition_models import (
    SubscriptionDeliveryRow,
    SubscriptionEditionRow,
)
from ase.domain.notification_delivery import EditionEmailPolicy, SubscriptionEmailPreferences


async def cancel_subscription_email(
    session: AsyncSession,
    user_id: UUID,
    subscription_id: UUID | None = None,
    preferences: SubscriptionEmailPreferences | None = None,
) -> None:
    query = update(SubscriptionDeliveryRow).where(
        SubscriptionDeliveryRow.channel == "email",
        SubscriptionDeliveryRow.destination_ref == user_id,
        SubscriptionDeliveryRow.state.in_(("pending", "unavailable", "sending")),
    )
    if subscription_id is not None:
        query = query.where(
            SubscriptionDeliveryRow.edition_id.in_(
                select(SubscriptionEditionRow.id).where(
                    SubscriptionEditionRow.subscription_id == subscription_id,
                )
            )
        )
    if preferences is not None:
        cancelled = []
        if not preferences.attention:
            cancelled.append("attention")
        if preferences.policy is not EditionEmailPolicy.EVERY:
            cancelled.append("edition_available")
        if preferences.policy is not EditionEmailPolicy.MATERIAL:
            cancelled.append("material_change")
        query = query.where(SubscriptionDeliveryRow.event_kind.in_(cancelled))
    await session.execute(
        query.values(
            state=case(
                (SubscriptionDeliveryRow.state == "sending", "uncertain"),
                else_="cancelled",
            ),
            safe_reason="opted_out",
        )
    )
