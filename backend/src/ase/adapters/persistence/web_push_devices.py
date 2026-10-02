"""Only the owner sees device IDs; endpoint credentials never return from storage."""

import hashlib
import json
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.web_push_models import PushDeliveryRow, PushDeviceRow
from ase.application.ports.llm import SecretCipher
from ase.domain.errors import InvalidRequest
from ase.domain.web_push import PushDevice, PushSubscription


class SqlPushDevices:
    def __init__(self, session: AsyncSession, cipher: SecretCipher) -> None:
        self._session, self._cipher = session, cipher

    async def list_for_user(self, user_id: UUID) -> tuple[PushDevice, ...]:
        rows = await self._session.scalars(
            select(PushDeviceRow)
            .where(
                PushDeviceRow.user_id == user_id,
            )
            .order_by(PushDeviceRow.created_at)
            .limit(10)
        )
        return tuple(PushDevice(row.id, row.endpoint_hash, row.created_at) for row in rows)

    async def register(
        self,
        user_id: UUID,
        family_id: UUID,
        security_version: int,
        subscription: PushSubscription,
        now: datetime,
    ) -> PushDevice:
        digest = hashlib.sha256(subscription.endpoint.encode()).hexdigest()
        existing = await self._session.scalar(
            select(PushDeviceRow).where(PushDeviceRow.endpoint_hash == digest)
        )
        if existing is not None:
            if existing.user_id != user_id or existing.family_id != family_id:
                raise InvalidRequest("Unsubscribe this browser before registering it again.")
            return PushDevice(existing.id, existing.endpoint_hash, existing.created_at)
        count = await self._session.scalar(
            select(func.count())
            .select_from(PushDeviceRow)
            .where(
                PushDeviceRow.user_id == user_id,
            )
        )
        if count is not None and count >= 10:
            raise InvalidRequest(
                "Remove a device before adding more than ten browser subscriptions."
            )
        row = PushDeviceRow(
            id=uuid4(),
            user_id=user_id,
            family_id=family_id,
            security_version=security_version,
            endpoint_hash=digest,
            encrypted_subscription=self._cipher.encrypt(
                json.dumps(
                    {
                        "endpoint": subscription.endpoint,
                        "p256dh": subscription.p256dh,
                        "auth": subscription.auth,
                    }
                )
            ),
            created_at=now,
            next_check_at=now,
        )
        self._session.add(row)
        await self._session.flush()
        return PushDevice(row.id, row.endpoint_hash, row.created_at)

    async def remove(self, user_id: UUID, device_id: UUID) -> None:
        await remove_push_rows(
            self._session,
            select(PushDeviceRow.id).where(
                PushDeviceRow.id == device_id,
                PushDeviceRow.user_id == user_id,
            ),
        )


async def remove_push_family(session: AsyncSession, family_id: UUID) -> None:
    await remove_push_rows(
        session, select(PushDeviceRow.id).where(PushDeviceRow.family_id == family_id)
    )


async def remove_push_user(session: AsyncSession, user_id: UUID) -> None:
    await remove_push_rows(
        session, select(PushDeviceRow.id).where(PushDeviceRow.user_id == user_id)
    )


async def remove_push_device(session: AsyncSession, device_id: UUID) -> None:
    await remove_push_rows(session, select(PushDeviceRow.id).where(PushDeviceRow.id == device_id))


async def remove_push_rows(session: AsyncSession, devices: Select[tuple[UUID]]) -> None:
    # Explicit child cleanup also works when a SQLite connection does not enable
    # foreign-key pragmas. The migration keeps ON DELETE CASCADE as defence in depth.
    await session.execute(delete(PushDeliveryRow).where(PushDeliveryRow.device_id.in_(devices)))
    await session.execute(delete(PushDeviceRow).where(PushDeviceRow.id.in_(devices)))


def decrypt_subscription(cipher: SecretCipher, row: PushDeviceRow) -> PushSubscription:
    value = json.loads(cipher.decrypt(row.encrypted_subscription))
    return PushSubscription(str(value["endpoint"]), str(value["p256dh"]), str(value["auth"]))
