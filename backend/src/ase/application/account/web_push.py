"""Explicit device opt-in is bound to the registering authenticated session family."""

import asyncio
import logging
from uuid import UUID

from ase.application.access import AccessPolicy
from ase.application.auth.current_session import validate_current_session
from ase.application.dto import AccessClaims
from ase.application.ports.repositories import RefreshTokenRepository, UnitOfWork, UserRepository
from ase.application.ports.services import Clock, RateLimiter
from ase.application.ports.web_push import (
    PushDeliveryStore,
    PushDeviceRepository,
    PushSender,
    PushValidator,
)
from ase.domain.errors import InvalidRequest, RateLimited
from ase.domain.web_push import PushDevice, PushOutcome, PushSubscription

log = logging.getLogger(__name__)


class WebPushService:
    def __init__(
        self,
        devices: PushDeviceRepository,
        validator: PushValidator,
        access: AccessPolicy,
        users: UserRepository,
        tokens: RefreshTokenRepository,
        clock: Clock,
        uow: UnitOfWork,
        available: bool,
        limiter: RateLimiter,
    ) -> None:
        self._devices, self._validator, self._access = devices, validator, access
        self._users, self._tokens, self._clock, self._uow = users, tokens, clock, uow
        self._available = available
        self._limiter = limiter

    async def list(self, claims: AccessClaims) -> tuple[PushDevice, ...]:
        actor = await validate_current_session(claims, self._users, self._tokens, self._clock)
        return await self._devices.list_for_user(actor.id)

    async def register(self, claims: AccessClaims, subscription: PushSubscription) -> PushDevice:
        retry = self._limiter.hit(f"push-register:{claims.user_id}", 20, 3600)
        if retry is not None:
            raise RateLimited(retry)
        if not self._available:
            raise InvalidRequest("Browser push is not configured for this installation.")
        await validate_current_session(claims, self._users, self._tokens, self._clock)
        # DNS and key validation happen before acquiring database locks.
        await self._validator.validate(subscription)
        actor = await validate_current_session(claims, self._users, self._tokens, self._clock)
        await self._access.context(actor, for_update=True)
        await validate_current_session(claims, self._users, self._tokens, self._clock)
        device = await self._devices.register(
            actor.id, claims.family_id, actor.security_version, subscription, self._clock.now()
        )
        await self._uow.commit()
        return device

    async def remove(self, claims: AccessClaims, device_id: UUID) -> None:
        actor = await validate_current_session(claims, self._users, self._tokens, self._clock)
        await self._access.context(actor, for_update=True)
        await self._devices.remove(actor.id, device_id)
        await self._uow.commit()


class WebPushWorker:
    def __init__(self, store: PushDeliveryStore, sender: PushSender, clock: Clock) -> None:
        self._store, self._sender, self._clock = store, sender, clock

    async def tick(self) -> int:
        await self._store.enqueue(self._clock.now())
        processed = 0
        for _ in range(25):
            delivery = await self._store.claim(self._clock.now())
            if delivery is None:
                break
            processed += 1
            if await self._store.authorise(delivery, self._clock.now()):
                try:
                    async with asyncio.timeout(15):
                        outcome = await self._sender.send(delivery, self._clock.now())
                except (TimeoutError, OSError):
                    outcome = PushOutcome.UNCERTAIN
                await self._store.finish(delivery, outcome, self._clock.now())
        return processed

    async def run(self) -> None:
        while True:
            try:
                await self.tick()
            except Exception:
                log.warning("web_push_tick_failed")
            await asyncio.sleep(30)
