"""Exclusive claims and lease-fenced terminal outcomes for bounded alert delivery."""

from collections.abc import Callable
from datetime import datetime, timedelta
from typing import cast
from uuid import uuid4

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ase.adapters.persistence.alert_delivery_prepare import prepare_alert_delivery
from ase.adapters.persistence.alert_routing_models import AlertNotificationRow as Outbox
from ase.application.access import AccessPolicy
from ase.application.ports.llm import SecretCipher
from ase.domain.alert_routing import AlertChannel, AlertDeliveryClaim, PreparedAlertDelivery
from ase.domain.notification_delivery import DeliveryOutcome

MAX_ATTEMPTS = 3


class SqlAlertDeliveryStore:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        access: Callable[[AsyncSession], AccessPolicy],
        cipher: SecretCipher,
        *,
        installation_url: str | None,
        base_url: str,
    ) -> None:
        self._sessions, self._access, self._cipher = sessions, access, cipher
        self._installation_url, self._base_url = installation_url, base_url

    async def recover_uncertain(self, now: datetime) -> None:
        async with self._sessions() as session:
            await session.execute(
                update(Outbox)
                .where(
                    Outbox.state == "sending",
                    Outbox.updated_at < now - timedelta(minutes=2),
                )
                .values(state="uncertain", safe_reason="worker_interrupted", updated_at=now)
            )
            await session.commit()

    async def claim(self, now: datetime) -> AlertDeliveryClaim | None:
        async with self._sessions() as session:
            eligible = (
                Outbox.state.in_(("pending", "unavailable")),
                Outbox.attempts < MAX_ATTEMPTS,
                or_(Outbox.next_attempt_at.is_(None), Outbox.next_attempt_at <= now),
            )
            candidate = await session.scalar(
                select(Outbox.id).where(*eligible).order_by(Outbox.created_at, Outbox.id).limit(1)
            )
            if candidate is None:
                return None
            lease = uuid4()
            row = await session.scalar(
                update(Outbox)
                .where(Outbox.id == candidate, *eligible)
                .values(
                    state="sending", lease_token=lease, attempts=Outbox.attempts + 1, updated_at=now
                )
                .returning(Outbox)
                .execution_options(synchronize_session=False)
            )
            if row is None:
                return None
            claim = AlertDeliveryClaim(
                row.id,
                row.alert_id,
                cast(AlertChannel, row.channel),
                row.destination_ref,
                lease,
                row.attempts,
            )
            await session.commit()
            return claim

    async def prepare(
        self, claim: AlertDeliveryClaim, now: datetime
    ) -> PreparedAlertDelivery | None:
        async with self._sessions() as session:
            row = await session.get(Outbox, claim.id)
            if row is None or row.lease_token != claim.lease_token or row.state != "sending":
                return None
            prepared, reason = await prepare_alert_delivery(
                session,
                row,
                self._access(session),
                self._cipher,
                installation_url=self._installation_url,
                base_url=self._base_url,
            )
            updated = await session.scalar(
                update(Outbox)
                .where(
                    Outbox.id == claim.id,
                    Outbox.lease_token == claim.lease_token,
                    Outbox.state == "sending",
                )
                .values(
                    state="cancelled" if reason else "sending", safe_reason=reason, updated_at=now
                )
                .returning(Outbox.id)
                .execution_options(synchronize_session=False)
            )
            # Release administration and account locks before any outbound request.
            await session.commit()
            return prepared if updated else None

    async def finish(
        self, claim: AlertDeliveryClaim, outcome: DeliveryOutcome, now: datetime
    ) -> None:
        state, reason, due = outcome.value, None, None
        if outcome is DeliveryOutcome.RETRYABLE:
            state = "pending" if claim.attempts < MAX_ATTEMPTS else "failed"
            reason, due = "transport_rejected", now + timedelta(minutes=5 * claim.attempts)
        elif outcome is DeliveryOutcome.UNAVAILABLE:
            state = "unavailable" if claim.attempts < MAX_ATTEMPTS else "failed"
            reason, due = "transport_unavailable", now + timedelta(minutes=15)
        elif outcome is DeliveryOutcome.UNCERTAIN:
            reason = "acceptance_unknown"
        async with self._sessions() as session:
            await session.execute(
                update(Outbox)
                .where(
                    Outbox.id == claim.id,
                    Outbox.lease_token == claim.lease_token,
                    Outbox.state == "sending",
                )
                .values(state=state, safe_reason=reason, next_attempt_at=due, updated_at=now)
            )
            await session.commit()
