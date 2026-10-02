"""Account opt-out fences pending alert mail in the same transaction."""

from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.alert_routing_models import AlertNotificationRow


async def cancel_alert_email(session: AsyncSession, user_id: UUID) -> None:
    # Re-enabling account mail must not revive work admitted before an opt-out.
    for previous, target in (
        ("pending", "cancelled"),
        ("unavailable", "cancelled"),
        ("sending", "uncertain"),
    ):
        await session.execute(
            update(AlertNotificationRow)
            .where(
                AlertNotificationRow.channel == "email",
                AlertNotificationRow.destination_ref == str(user_id),
                AlertNotificationRow.state == previous,
            )
            .values(state=target, safe_reason="opted_out")
        )
