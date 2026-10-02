"""Device registration and external delivery boundaries."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from ase.domain.web_push import PushDelivery, PushDevice, PushOutcome, PushSubscription


class PushDeviceRepository(Protocol):
    async def list_for_user(self, user_id: UUID) -> tuple[PushDevice, ...]: ...
    async def register(
        self,
        user_id: UUID,
        family_id: UUID,
        security_version: int,
        subscription: PushSubscription,
        now: datetime,
    ) -> PushDevice: ...
    async def remove(self, user_id: UUID, device_id: UUID) -> None: ...


class PushValidator(Protocol):
    async def validate(self, subscription: PushSubscription) -> None: ...


class PushSender(Protocol):
    async def send(self, delivery: PushDelivery, now: datetime) -> PushOutcome: ...


class PushDeliveryStore(Protocol):
    async def enqueue(self, now: datetime) -> None: ...
    async def claim(self, now: datetime) -> PushDelivery | None: ...
    async def authorise(self, delivery: PushDelivery, now: datetime) -> bool: ...
    async def finish(self, delivery: PushDelivery, outcome: PushOutcome, now: datetime) -> None: ...
