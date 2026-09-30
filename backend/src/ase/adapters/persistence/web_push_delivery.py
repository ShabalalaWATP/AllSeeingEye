"""Exclusive push claims are reauthorised against the live account, session and alert."""

from collections.abc import Callable
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ase.adapters.persistence.access import visibility_predicate
from ase.adapters.persistence.operational_models import AlertRow
from ase.adapters.persistence.web_push_admission import device_access, enqueue_push, push_visibility
from ase.adapters.persistence.web_push_devices import decrypt_subscription, remove_push_device
from ase.adapters.persistence.web_push_models import PushDeliveryRow, PushDeviceRow
from ase.adapters.security.cipher import CipherUnavailable
from ase.application.access import AccessPolicy
from ase.application.ports.llm import SecretCipher
from ase.domain.errors import Forbidden, NotFound, Unauthenticated
from ase.domain.web_push import PushDelivery, PushOutcome


class SqlPushDeliveryStore:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        access: Callable[[AsyncSession], AccessPolicy],
        cipher: SecretCipher,
    ) -> None:
        self._sessions, self._access, self._cipher = sessions, access, cipher

    async def enqueue(self, now: datetime) -> None:
        await enqueue_push(self._sessions, self._access, now)

    async def claim(self, now: datetime) -> PushDelivery | None:
        async with self._sessions() as session:
            candidate = await session.scalar(
                select(PushDeliveryRow.id)
                .where(
                    PushDeliveryRow.state == "pending",
                )
                .order_by(PushDeliveryRow.created_at, PushDeliveryRow.id)
                .limit(1)
            )
            if candidate is None:
                return None
            lease = uuid4()
            row = await session.scalar(
                update(PushDeliveryRow)
                .where(
                    PushDeliveryRow.id == candidate,
                    PushDeliveryRow.state == "pending",
                )
                .values(state="sending", lease_token=lease, updated_at=now)
                .returning(PushDeliveryRow)
            )
            if row is None:
                return None
            device = await session.get(PushDeviceRow, row.device_id)
            if device is None:
                await session.execute(delete(PushDeliveryRow).where(PushDeliveryRow.id == row.id))
                await session.commit()
                return None
            try:
                subscription = decrypt_subscription(self._cipher, device)
            except (CipherUnavailable, ValueError, TypeError, KeyError):
                row.state = "refused"
                await session.commit()
                return None
            delivery = PushDelivery(row.id, row.device_id, row.alert_id, lease, subscription)
            await session.commit()
            return delivery

    async def authorise(self, delivery: PushDelivery, now: datetime) -> bool:
        async with self._sessions() as session:
            device = await session.get(PushDeviceRow, delivery.device_id)
            if device is None:
                return False
            try:
                current = await device_access(session, self._access(session), device, now)
            except (Forbidden, NotFound, Unauthenticated):
                await remove_push_device(session, device.id)
                await session.commit()
                return False
            visible = await session.scalar(
                select(AlertRow.id).where(
                    AlertRow.id == delivery.alert_id,
                    AlertRow.fired_at >= now - timedelta(days=1),
                    visibility_predicate(
                        AlertRow.created_by, AlertRow.team_id, push_visibility(current)
                    ),
                )
            )
            owned = await session.scalar(
                update(PushDeliveryRow)
                .where(
                    PushDeliveryRow.id == delivery.id,
                    PushDeliveryRow.state == "sending",
                    PushDeliveryRow.lease_token == delivery.lease_token,
                )
                .values(state="sending" if visible else "cancelled", updated_at=now)
                .returning(PushDeliveryRow.id)
            )
            await session.commit()
            return visible is not None and owned is not None

    async def finish(self, delivery: PushDelivery, outcome: PushOutcome, now: datetime) -> None:
        async with self._sessions() as session:
            await session.execute(
                update(PushDeliveryRow)
                .where(
                    PushDeliveryRow.id == delivery.id,
                    PushDeliveryRow.state == "sending",
                    PushDeliveryRow.lease_token == delivery.lease_token,
                )
                .values(state=outcome.value, updated_at=now)
            )
            if outcome is PushOutcome.EXPIRED:
                await remove_push_device(session, delivery.device_id)
            await session.commit()
