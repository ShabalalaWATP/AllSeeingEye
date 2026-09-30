"""Bounded outbox work; unknown network outcomes never automatically retry."""

import asyncio
import logging

from ase.application.ports.notification_delivery import (
    NotificationDeliveryStore,
    NotificationEmailSender,
)
from ase.application.ports.services import Clock
from ase.domain.notification_delivery import DeliveryOutcome

log = logging.getLogger(__name__)


class NotificationDispatcher:
    def __init__(
        self,
        store: NotificationDeliveryStore,
        sender: NotificationEmailSender,
        clock: Clock,
    ) -> None:
        self._store, self._sender, self._clock = store, sender, clock

    async def tick(self) -> int:
        await self._store.recover_uncertain(self._clock.now())
        processed = 0
        for _ in range(25):
            claim = await self._store.claim(self._clock.now())
            if claim is None:
                break
            processed += 1
            message = await self._store.prepare(claim, self._clock.now())
            if message is None:
                continue
            outcome = DeliveryOutcome.UNAVAILABLE
            if self._sender.available:
                try:
                    async with asyncio.timeout(40):
                        outcome = await self._sender.send(message)
                except (TimeoutError, OSError):
                    outcome = DeliveryOutcome.UNCERTAIN
                # Cancellation/crash leaves 'sending'. Recovery marks it uncertain,
                # never pending, because a relay may have accepted the message.
            await self._store.finish(claim, outcome, self._clock.now())
        return processed

    async def run(self) -> None:
        while True:
            try:
                await self.tick()
            except Exception:
                # A temporary database error must not silently end all future delivery.
                # No exception text: transports may embed addresses or message data.
                log.warning("notification_worker_tick_failed")
            await asyncio.sleep(30)
