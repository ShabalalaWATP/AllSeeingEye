"""Exclusive CAS claims, fresh access and explicit uncertainty for SMTP outbox work."""

from collections.abc import Callable
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ase.adapters.persistence.notification_preferences import SqlNotificationPreferences
from ase.adapters.persistence.operational_models import ScheduleRow
from ase.adapters.persistence.subscription_edition_models import (
    SubscriptionDeliveryRow,
    SubscriptionEditionRow,
)
from ase.application.access import AccessPolicy
from ase.domain.errors import Forbidden, NotFound, Unauthenticated
from ase.domain.notification_delivery import (
    ClaimedDelivery,
    DeliveryOutcome,
    EditionEmailPolicy,
    NotificationEmail,
)

MAX_ATTEMPTS = 3


class SqlEditionDeliveryStore:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        access: Callable[[AsyncSession], AccessPolicy],
        base_url: str,
    ) -> None:
        self._sessions, self._access, self._base_url = sessions, access, base_url.rstrip("/")

    async def recover_uncertain(self, now: datetime) -> None:
        async with self._sessions() as session:
            await session.execute(
                update(SubscriptionDeliveryRow)
                .where(
                    SubscriptionDeliveryRow.channel == "email",
                    SubscriptionDeliveryRow.state == "sending",
                    SubscriptionDeliveryRow.updated_at < now - timedelta(minutes=2),
                )
                .values(state="uncertain", safe_reason="worker_interrupted", updated_at=now)
            )
            await session.commit()

    async def claim(self, now: datetime) -> ClaimedDelivery | None:
        async with self._sessions() as session:
            eligible = (
                SubscriptionDeliveryRow.channel == "email",
                SubscriptionDeliveryRow.destination_ref.is_not(None),
                SubscriptionDeliveryRow.state.in_(("pending", "unavailable")),
                SubscriptionDeliveryRow.attempts < MAX_ATTEMPTS,
                or_(
                    SubscriptionDeliveryRow.next_attempt_at.is_(None),
                    SubscriptionDeliveryRow.next_attempt_at <= now,
                ),
            )
            candidate = await session.scalar(
                select(SubscriptionDeliveryRow.id)
                .where(*eligible)
                .order_by(SubscriptionDeliveryRow.created_at, SubscriptionDeliveryRow.id)
                .limit(1)
            )
            if candidate is None:
                return None
            lease = uuid4()
            row = await session.scalar(
                update(SubscriptionDeliveryRow)
                .where(
                    SubscriptionDeliveryRow.id == candidate,
                    *eligible,
                )
                .values(
                    state="sending",
                    lease_token=lease,
                    attempts=SubscriptionDeliveryRow.attempts + 1,
                    updated_at=now,
                )
                .returning(SubscriptionDeliveryRow)
                .execution_options(synchronize_session=False)
            )
            if row is None or row.destination_ref is None:
                return None
            claim = ClaimedDelivery(
                row.id,
                row.edition_id,
                row.destination_ref,
                row.event_kind,
                lease,
                row.attempts,
            )
            await session.commit()
            return claim

    async def prepare(self, claim: ClaimedDelivery, now: datetime) -> NotificationEmail | None:
        async with self._sessions() as session:
            outbox = await session.get(SubscriptionDeliveryRow, claim.id)
            if (
                outbox is None
                or outbox.lease_token != claim.lease_token
                or outbox.state != "sending"
            ):
                return None
            edition = await session.get(SubscriptionEditionRow, claim.resource_id)
            schedule = await session.get(ScheduleRow, edition.subscription_id) if edition else None
            reason = None
            message = None
            if schedule is None or not schedule.enabled or schedule.archived_at is not None:
                reason = "subscription_unavailable"
            else:
                try:
                    origin = (schedule.created_by, schedule.team_id)
                    access = await self._access(session).background(
                        claim.recipient_id,
                        schedule.team_id,
                        for_update=True,
                    )
                    schedule = await session.get(ScheduleRow, schedule.id, populate_existing=True)
                    if (
                        schedule is None
                        or not schedule.enabled
                        or schedule.archived_at is not None
                        or (schedule.created_by, schedule.team_id) != origin
                    ):
                        raise NotFound()
                    access.require_read(schedule.created_by, schedule.team_id)
                    if schedule.team_id is None and schedule.created_by != claim.recipient_id:
                        raise NotFound()
                    preferences = SqlNotificationPreferences(session)
                    account = await preferences.email(claim.recipient_id)
                    subscription = await preferences.subscription(claim.recipient_id, schedule.id)
                    allowed = (
                        subscription.attention
                        if claim.event_kind == "attention"
                        else subscription.policy
                        is (
                            EditionEmailPolicy.EVERY
                            if claim.event_kind == "edition_available"
                            else EditionEmailPolicy.MATERIAL
                        )
                    )
                    if not account.enabled or not allowed:
                        reason = "opted_out"
                    elif not await preferences.email_confirmed(claim.recipient_id):
                        reason = "email_unconfirmed"
                    else:
                        label = {
                            "edition_available": "A subscription edition is available",
                            "material_change": "A subscription has changed materially",
                            "attention": "A subscription needs attention",
                        }[claim.event_kind]
                        name = f"\nSubscription: {schedule.name}\n" if account.include_names else ""
                        link = (
                            f"{self._base_url}/subscriptions?subscription={schedule.id}"
                            f"&edition={claim.resource_id}"
                        )
                        message = NotificationEmail(
                            access.actor.email,
                            "The All Seeing Eye: subscription notification",
                            f"{label}.{name}\n\nOpen securely: {link}\n\n"
                            f"Manage email preferences: {self._base_url}"
                            "/account?section=notifications",
                        )
                except (Forbidden, NotFound, Unauthenticated):
                    reason = "access_revoked"
            if reason is not None:
                outbox.state, outbox.safe_reason, outbox.updated_at = "cancelled", reason, now
            elif message is not None:
                # Recovery may have fenced an old claim while authorisation waited.
                owned = await session.scalar(
                    update(SubscriptionDeliveryRow)
                    .where(
                        SubscriptionDeliveryRow.id == claim.id,
                        SubscriptionDeliveryRow.lease_token == claim.lease_token,
                        SubscriptionDeliveryRow.state == "sending",
                    )
                    .values(updated_at=now)
                    .returning(SubscriptionDeliveryRow.id)
                )
                if owned is None:
                    message = None
            # Release all account/administration locks before SMTP network work.
            await session.commit()
            return message

    async def finish(
        self,
        claim: ClaimedDelivery,
        outcome: DeliveryOutcome,
        now: datetime,
    ) -> None:
        state = outcome.value
        attempts = claim.attempts
        next_attempt = None
        reason = None
        if outcome is DeliveryOutcome.RETRYABLE:
            state = "pending" if attempts < MAX_ATTEMPTS else "failed"
            next_attempt = now + timedelta(minutes=5 * attempts)
            reason = "transport_rejected"
        elif outcome is DeliveryOutcome.UNAVAILABLE:
            attempts -= 1
            next_attempt = now + timedelta(minutes=15)
            reason = "email_not_configured"
        elif outcome is DeliveryOutcome.UNCERTAIN:
            reason = "acceptance_unknown"
        async with self._sessions() as session:
            await session.execute(
                update(SubscriptionDeliveryRow)
                .where(
                    SubscriptionDeliveryRow.id == claim.id,
                    SubscriptionDeliveryRow.lease_token == claim.lease_token,
                    SubscriptionDeliveryRow.state == "sending",
                )
                .values(
                    state=state,
                    attempts=attempts,
                    safe_reason=reason,
                    next_attempt_at=next_attempt,
                    updated_at=now,
                )
            )
            await session.commit()
