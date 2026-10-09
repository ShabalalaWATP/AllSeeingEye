"""Bounded recipient projection starts at opt-in and excludes durable seen receipts."""

from collections.abc import Callable
from datetime import datetime, timedelta
from uuid import UUID, uuid5

from sqlalchemy import delete, exists, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ase.adapters.persistence.access import visibility_predicate
from ase.adapters.persistence.operational_models import AlertRow
from ase.adapters.persistence.web_push_devices import remove_push_device
from ase.adapters.persistence.web_push_models import PushDeliveryRow, PushDeviceRow
from ase.application.access import AccessContext, AccessPolicy
from ase.application.ports import RefreshTokenRepository
from ase.domain.access import Visibility
from ase.domain.errors import Forbidden, NotFound, Unauthenticated

NAMESPACE = UUID("ef669ff2-851e-4ffc-b912-35840b38c8a1")


async def device_access(
    session: AsyncSession,
    access: AccessPolicy,
    device: PushDeviceRow,
    now: datetime,
    tokens: RefreshTokenRepository,
) -> AccessContext:
    current = await access.background(device.user_id, None, for_update=True)
    if (
        current.actor.security_version != device.security_version
        or not await tokens.family_is_active(
            device.user_id,
            device.family_id,
            now,
            require_mfa=current.actor.is_admin,
        )
    ):
        raise Forbidden()
    return current


def push_visibility(access: AccessContext) -> Visibility:
    return Visibility(
        access.actor.id,
        False,
        tuple(
            team_id
            for team_id in access.memberships
            if team_id in access.teams and access.teams[team_id].is_active
        ),
    )


async def enqueue_push(
    sessions: async_sessionmaker[AsyncSession],
    access: Callable[[AsyncSession], AccessPolicy],
    now: datetime,
    tokens: Callable[[AsyncSession], RefreshTokenRepository],
) -> None:
    async with sessions() as session:
        await session.execute(
            update(PushDeliveryRow)
            .where(
                PushDeliveryRow.state == "sending",
                PushDeliveryRow.updated_at < now - timedelta(minutes=1),
            )
            .values(state="uncertain", updated_at=now)
        )
        await session.execute(
            delete(PushDeliveryRow).where(PushDeliveryRow.created_at < now - timedelta(days=7))
        )
        ids = list(
            await session.scalars(
                select(PushDeviceRow.id)
                .where(
                    PushDeviceRow.next_check_at <= now,
                )
                .order_by(PushDeviceRow.next_check_at, PushDeviceRow.id)
                .limit(100)
            )
        )
        await session.commit()
    for device_id in ids:
        async with sessions() as session:
            device = await session.get(PushDeviceRow, device_id)
            if device is None:
                continue
            try:
                current = await device_access(
                    session, access(session), device, now, tokens(session)
                )
            except (Forbidden, NotFound, Unauthenticated):
                await remove_push_device(session, device_id)
                await session.commit()
                continue
            device = await session.get(PushDeviceRow, device_id, populate_existing=True)
            if device is None or device.next_check_at > now:
                continue
            alerts = list(
                await session.scalars(
                    select(AlertRow.id)
                    .where(
                        visibility_predicate(
                            AlertRow.created_by, AlertRow.team_id, push_visibility(current)
                        ),
                        AlertRow.fired_at >= now - timedelta(days=1),
                        AlertRow.fired_at >= device.created_at,
                        ~exists().where(
                            PushDeliveryRow.device_id == device.id,
                            PushDeliveryRow.alert_id == AlertRow.id,
                        ),
                    )
                    .order_by(AlertRow.fired_at, AlertRow.id)
                    .limit(25)
                )
            )
            insert = sqlite_insert if session.get_bind().dialect.name == "sqlite" else pg_insert
            for alert_id in alerts:
                await session.execute(
                    insert(PushDeliveryRow)
                    .values(
                        id=uuid5(NAMESPACE, f"{device.id}:{alert_id}"),
                        device_id=device.id,
                        alert_id=alert_id,
                        state="pending",
                        created_at=now,
                        updated_at=now,
                    )
                    .on_conflict_do_nothing()
                )
            device.next_check_at = now + timedelta(seconds=30)
            await session.commit()
