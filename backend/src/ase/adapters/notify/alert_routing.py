"""Every webhook send uses the same public-address validation and DNS pinning as registration."""

import asyncio

from ase.adapters.feeds.http import FeedFetchError, assert_public_host
from ase.adapters.notify.webhook import WebhookNotifier
from ase.application.ports.notification_delivery import NotificationEmailSender
from ase.domain.alert_routing import PreparedAlertDelivery
from ase.domain.errors import InvalidRequest
from ase.domain.notification_delivery import DeliveryOutcome


class PublicAlertWebhookValidator:
    async def validate(self, url: str) -> None:
        try:
            WebhookNotifier(url, "ase-destination-validation")
            async with asyncio.timeout(10):
                await assert_public_host(url)
        except (ValueError, FeedFetchError, OSError, TimeoutError):
            raise InvalidRequest(
                "Webhook destinations must use HTTPS and public addresses."
            ) from None


class RoutedAlertSender:
    def __init__(self, email: NotificationEmailSender, user_agent: str) -> None:
        self._email, self._user_agent = email, user_agent

    async def send(self, delivery: PreparedAlertDelivery) -> DeliveryOutcome:
        if delivery.email is not None:
            if not self._email.available:
                return DeliveryOutcome.UNAVAILABLE
            return await self._email.send(delivery.email)
        if delivery.webhook_url is not None:
            return await WebhookNotifier(delivery.webhook_url, self._user_agent).send_outcome(
                delivery.alert, delivery.indicator
            )
        return DeliveryOutcome.UNAVAILABLE
