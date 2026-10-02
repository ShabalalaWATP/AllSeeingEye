"""Destination URLs cross only the encrypted storage boundary, never a read response."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.alert_routing_models import (
    AlertRoutingRow,
    AlertWebhookDestinationRow,
)
from ase.application.ports.llm import SecretCipher
from ase.domain.alert_routing import AlertRoute, AlertWebhookDestination
from ase.domain.errors import InvalidRequest


def destination_from_row(row: AlertWebhookDestinationRow) -> AlertWebhookDestination:
    return AlertWebhookDestination(
        row.id, row.name, row.created_by, row.team_id, row.enabled, row.created_at
    )


class SqlAlertRoutingRepository:
    def __init__(self, session: AsyncSession, cipher: SecretCipher) -> None:
        self._session, self._cipher = session, cipher

    async def route(self, indicator_id: UUID) -> AlertRoute | None:
        row = await self._session.get(AlertRoutingRow, indicator_id, populate_existing=True)
        return (
            AlertRoute(
                row.indicator_id, row.configured_by, row.email_enabled, row.webhook_id, row.revision
            )
            if row
            else None
        )

    async def save_route(self, route: AlertRoute) -> None:
        await self._session.merge(
            AlertRoutingRow(
                indicator_id=route.indicator_id,
                configured_by=route.configured_by,
                email_enabled=route.email_enabled,
                webhook_id=route.webhook_id,
                revision=route.revision,
            )
        )
        await self._session.flush()

    async def destination(self, destination_id: UUID) -> AlertWebhookDestination | None:
        row = await self._session.get(
            AlertWebhookDestinationRow, destination_id, populate_existing=True
        )
        return destination_from_row(row) if row else None

    async def destinations(
        self, owner_id: UUID, team_id: UUID | None
    ) -> list[AlertWebhookDestination]:
        scope = AlertWebhookDestinationRow.team_id == team_id
        if team_id is None:
            scope &= AlertWebhookDestinationRow.created_by == owner_id
        rows = await self._session.scalars(
            select(AlertWebhookDestinationRow)
            .where(scope, AlertWebhookDestinationRow.enabled.is_(True))
            .order_by(AlertWebhookDestinationRow.name)
            .limit(20)
        )
        return [destination_from_row(row) for row in rows]

    async def add_destination(self, destination: AlertWebhookDestination, url: str) -> None:
        if not self._cipher.available:
            raise InvalidRequest("Webhook credential storage is unavailable.")
        self._session.add(
            AlertWebhookDestinationRow(
                id=destination.id,
                name=destination.name,
                created_by=destination.created_by,
                team_id=destination.team_id,
                enabled=True,
                created_at=destination.created_at,
                url_encrypted=self._cipher.encrypt(url),
            )
        )
        await self._session.flush()

    async def disable_destination(self, destination_id: UUID) -> None:
        row = await self._session.get(AlertWebhookDestinationRow, destination_id)
        if row:
            row.enabled = False
            await self._session.flush()
