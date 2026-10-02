"""Delivery failure never rolls back an alert or prevents other selected channels."""

import asyncio
import logging

from ase.application.ports import Clock
from ase.application.ports.alert_routing import AlertDeliverySender, AlertDeliveryStore
from ase.domain.notification_delivery import DeliveryOutcome

log = logging.getLogger(__name__)


class AlertNotificationDispatcher:
    def __init__(
        self, store: AlertDeliveryStore, sender: AlertDeliverySender, clock: Clock
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
            prepared = await self._store.prepare(claim, self._clock.now())
            if prepared is None:
                continue
            try:
                async with asyncio.timeout(40):
                    outcome = await self._sender.send(prepared)
            except Exception:
                # Transport errors can contain credentials. Unknown outcomes are terminal.
                outcome = DeliveryOutcome.UNCERTAIN
            await self._store.finish(claim, outcome, self._clock.now())
        return processed

    async def run(self) -> None:
        while True:
            try:
                await self.tick()
            except Exception:
                log.warning("alert_notification_worker_tick_failed")
            await asyncio.sleep(30)
