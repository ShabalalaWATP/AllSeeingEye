"""Boundaries for scoped destinations and durable alert delivery."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from ase.domain.alert_routing import (
    AlertDeliveryClaim,
    AlertRoute,
    AlertWebhookDestination,
    PreparedAlertDelivery,
)
from ase.domain.notification_delivery import DeliveryOutcome


class AlertRoutingRepository(Protocol):
    async def route(self, indicator_id: UUID) -> AlertRoute | None: ...
    async def save_route(self, route: AlertRoute) -> None: ...
    async def destination(self, destination_id: UUID) -> AlertWebhookDestination | None: ...
    async def destinations(
        self, owner_id: UUID, team_id: UUID | None
    ) -> list[AlertWebhookDestination]: ...
    async def add_destination(self, destination: AlertWebhookDestination, url: str) -> None: ...
    async def disable_destination(self, destination_id: UUID) -> None: ...


class AlertWebhookValidator(Protocol):
    async def validate(self, url: str) -> None: ...


class AlertDeliveryStore(Protocol):
    async def recover_uncertain(self, now: datetime) -> None: ...
    async def claim(self, now: datetime) -> AlertDeliveryClaim | None: ...
    async def prepare(
        self, claim: AlertDeliveryClaim, now: datetime
    ) -> PreparedAlertDelivery | None: ...
    async def finish(
        self, claim: AlertDeliveryClaim, outcome: DeliveryOutcome, now: datetime
    ) -> None: ...


class AlertDeliverySender(Protocol):
    async def send(self, delivery: PreparedAlertDelivery) -> DeliveryOutcome: ...
