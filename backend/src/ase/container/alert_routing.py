"""Scoped route management and durable delivery wiring."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.notify.alert_routing import PublicAlertWebhookValidator, RoutedAlertSender
from ase.adapters.persistence.alert_notification_delivery import SqlAlertDeliveryStore
from ase.adapters.persistence.alert_routing import SqlAlertRoutingRepository
from ase.application.warning.notification_dispatch import AlertNotificationDispatcher
from ase.application.warning.notification_routing import AlertRoutingService
from ase.container.notifications import notification_sender

if TYPE_CHECKING:
    from ase.container import Container


def alert_routing(container: Container, session: AsyncSession) -> AlertRoutingService:
    repos = container.repositories(session)
    return AlertRoutingService(
        SqlAlertRoutingRepository(session, container.cipher),
        repos.indicators,
        container.access_policy(session),
        PublicAlertWebhookValidator(),
        container.clock,
        repos.uow,
        container._auditor(repos),
    )


def alert_dispatcher(container: Container) -> AlertNotificationDispatcher:
    settings = container.settings
    return AlertNotificationDispatcher(
        SqlAlertDeliveryStore(
            container.session_factory,
            container.access_policy,
            container.cipher,
            installation_url=settings.alert_webhook_url,
            base_url=settings.public_base_url,
        ),
        RoutedAlertSender(notification_sender(container), settings.feeds_user_agent),
        container.clock,
    )
