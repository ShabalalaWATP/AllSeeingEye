"""Opt-ins are separate rows; migrations never enrol existing users."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.mfa_models import EmailMfaRow
from ase.adapters.persistence.notification_models import (
    NotificationPreferenceRow,
    SubscriptionNotificationRow,
)
from ase.domain.errors import InvalidRequest
from ase.domain.notification_delivery import (
    EditionEmailPolicy,
    EmailPreferences,
    SubscriptionEmailPreferences,
)


class SqlNotificationPreferences:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def email(self, user_id: UUID) -> EmailPreferences:
        row = await self._session.get(NotificationPreferenceRow, user_id, populate_existing=True)
        return EmailPreferences(row.email_enabled, row.include_names) if row else EmailPreferences()

    async def save_email(self, user_id: UUID, settings: EmailPreferences) -> None:
        await self._session.merge(
            NotificationPreferenceRow(
                user_id=user_id,
                email_enabled=settings.enabled,
                include_names=settings.include_names,
            )
        )

    async def email_confirmed(self, user_id: UUID) -> bool:
        return bool(
            await self._session.scalar(
                select(EmailMfaRow.enabled).where(EmailMfaRow.user_id == user_id)
            )
        )

    async def subscription(
        self,
        user_id: UUID,
        subscription_id: UUID,
    ) -> SubscriptionEmailPreferences:
        row = await self._session.get(
            SubscriptionNotificationRow,
            (user_id, subscription_id),
            populate_existing=True,
        )
        return (
            SubscriptionEmailPreferences(
                EditionEmailPolicy(row.email_policy),
                row.attention,
            )
            if row
            else SubscriptionEmailPreferences()
        )

    async def save_subscription(
        self,
        user_id: UUID,
        subscription_id: UUID,
        settings: SubscriptionEmailPreferences,
    ) -> None:
        existing = await self._session.get(SubscriptionNotificationRow, (user_id, subscription_id))
        if existing is None:
            count = await self._session.scalar(
                select(func.count())
                .select_from(SubscriptionNotificationRow)
                .where(SubscriptionNotificationRow.subscription_id == subscription_id)
            )
            if count is not None and count >= 100:
                raise InvalidRequest("This subscription has reached its 100-recipient limit.")
        await self._session.merge(
            SubscriptionNotificationRow(
                user_id=user_id,
                subscription_id=subscription_id,
                email_policy=settings.policy.value,
                attention=settings.attention,
            )
        )
