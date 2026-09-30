"""Notification adapters assembled without broadening the shared account model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.notify.notification_email import (
    NullNotificationEmailSender,
    SmtpNotificationEmailSender,
)
from ase.adapters.persistence.notification_delivery import SqlEditionDeliveryStore
from ase.adapters.persistence.notification_feed import SqlPrivateFeedRepository
from ase.adapters.persistence.notification_preferences import SqlNotificationPreferences
from ase.application.account.notification_dispatch import NotificationDispatcher
from ase.application.account.notification_preferences import NotificationPreferences
from ase.application.account.private_feed import PrivateFeedService
from ase.application.ports.notification_delivery import NotificationEmailSender

if TYPE_CHECKING:
    from ase.container import Container


def private_feed(container: Container, session: AsyncSession) -> PrivateFeedService:
    repos = container.repositories(session)
    return PrivateFeedService(
        SqlPrivateFeedRepository(session),
        repos.users,
        container.access_policy(session),
        container.generator,
        container.limiter,
        container.clock,
        repos.uow,
        container.settings.public_base_url,
    )


def notification_preferences(
    container: Container, session: AsyncSession
) -> NotificationPreferences:
    repos = container.repositories(session)
    return NotificationPreferences(
        SqlNotificationPreferences(session),
        repos.schedules,
        container.access_policy(session),
        repos.uow,
    )


def notification_sender(container: Container) -> NotificationEmailSender:
    settings = container.settings
    if not settings.smtp_host or not settings.smtp_from_email:
        return NullNotificationEmailSender()
    return SmtpNotificationEmailSender(
        host=settings.smtp_host,
        port=settings.smtp_port,
        security=settings.smtp_security,
        from_email=str(settings.smtp_from_email),
        username=settings.smtp_username,
        password=settings.smtp_password.get_secret_value() if settings.smtp_password else None,
        timeout=settings.smtp_timeout_seconds,
    )


def notification_dispatcher(container: Container) -> NotificationDispatcher:
    return NotificationDispatcher(
        SqlEditionDeliveryStore(
            container.session_factory, container.access_policy, container.settings.public_base_url
        ),
        notification_sender(container),
        container.clock,
    )
