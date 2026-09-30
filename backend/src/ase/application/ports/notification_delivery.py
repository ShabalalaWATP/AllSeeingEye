"""Network outcomes and commit-owning outbox boundary for notification workers."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from ase.domain.notification_delivery import (
    ClaimedDelivery,
    DeliveryOutcome,
    EmailPreferences,
    NotificationEmail,
    SubscriptionEmailPreferences,
)


class NotificationEmailSender(Protocol):
    @property
    def available(self) -> bool: ...
    async def send(self, message: NotificationEmail) -> DeliveryOutcome: ...


class NotificationPreferenceRepository(Protocol):
    async def email(self, user_id: UUID) -> EmailPreferences: ...
    async def save_email(self, user_id: UUID, settings: EmailPreferences) -> None: ...
    async def email_confirmed(self, user_id: UUID) -> bool: ...
    async def subscription(
        self,
        user_id: UUID,
        subscription_id: UUID,
    ) -> SubscriptionEmailPreferences: ...
    async def save_subscription(
        self,
        user_id: UUID,
        subscription_id: UUID,
        settings: SubscriptionEmailPreferences,
    ) -> None: ...


class EditionDeliveryStore(Protocol):
    async def recover_uncertain(self, now: datetime) -> None: ...
    async def claim(self, now: datetime) -> ClaimedDelivery | None: ...
    async def prepare(
        self,
        claim: ClaimedDelivery,
        now: datetime,
    ) -> NotificationEmail | None:
        """Recheck live authorisation/preferences; cancel invalid intents atomically."""
        ...

    async def finish(
        self,
        claim: ClaimedDelivery,
        outcome: DeliveryOutcome,
        now: datetime,
    ) -> None: ...
