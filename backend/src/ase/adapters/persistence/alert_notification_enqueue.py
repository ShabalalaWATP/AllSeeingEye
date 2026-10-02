"""Enqueue each selected destination once, in the alert's existing transaction."""

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.alert_routing_models import AlertNotificationRow, AlertRoutingRow
from ase.adapters.persistence.notification_preferences import SqlNotificationPreferences
from ase.domain.warning import Alert


async def enqueue_alert_notifications(
    session: AsyncSession,
    alert: Alert,
    *,
    installation_copy: bool,
) -> None:
    route = await session.get(AlertRoutingRow, alert.indicator_id) if alert.indicator_id else None
    choices: list[tuple[str, str, int]] = []
    if installation_copy:
        choices.append(("installation_webhook", "installation", 0))
    if route:
        if route.email_enabled:
            preferences = SqlNotificationPreferences(session)
            account = await preferences.email(route.configured_by)
            if account.enabled and await preferences.email_confirmed(route.configured_by):
                choices.append(("email", str(route.configured_by), route.revision))
        if route.webhook_id:
            choices.append(("webhook", str(route.webhook_id), route.revision))
    for channel, destination, revision in choices:
        exists = await session.scalar(
            select(AlertNotificationRow.id).where(
                AlertNotificationRow.alert_id == alert.id,
                AlertNotificationRow.channel == channel,
                AlertNotificationRow.destination_ref == destination,
            )
        )
        if exists is None:
            session.add(
                AlertNotificationRow(
                    id=uuid4(),
                    alert_id=alert.id,
                    channel=channel,
                    destination_ref=destination,
                    route_revision=revision,
                    state="pending",
                    attempts=0,
                    created_at=alert.fired_at,
                    updated_at=alert.fired_at,
                )
            )
    await session.flush()
