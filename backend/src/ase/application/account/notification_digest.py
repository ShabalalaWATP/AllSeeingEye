"""Opt-in digest scheduling uses the same delivery dispatcher and outcome policy."""

import asyncio
import logging

from ase.application.access import AccessPolicy
from ase.application.account.notification_dispatch import NotificationDispatcher
from ase.application.ports.notification_delivery import NotificationPreferenceRepository
from ase.application.ports.notification_digest import (
    DigestPreferenceRepository,
    DigestSchedulerStore,
)
from ase.application.ports.repositories import UnitOfWork
from ase.application.ports.services import Clock
from ase.domain.errors import InvalidRequest
from ase.domain.notification_digest import DigestPreferences
from ase.domain.users import User

log = logging.getLogger(__name__)


class DigestPreferenceService:
    def __init__(
        self,
        repository: DigestPreferenceRepository,
        email: NotificationPreferenceRepository,
        access: AccessPolicy,
        clock: Clock,
        uow: UnitOfWork,
    ) -> None:
        self._repository, self._email, self._access = repository, email, access
        self._clock, self._uow = clock, uow

    async def get(self, actor: User) -> DigestPreferences:
        await self._access.context(actor)
        return await self._repository.get(actor.id)

    async def save(self, actor: User, preferences: DigestPreferences) -> None:
        await self._access.context(actor, for_update=True)
        if preferences.enabled:
            email = await self._email.email(actor.id)
            if not email.enabled or not await self._email.email_confirmed(actor.id):
                raise InvalidRequest(
                    "Enable account email after confirming address ownership first."
                )
        await self._repository.save(actor.id, preferences, self._clock.now())
        await self._uow.commit()


class DigestWorker:
    def __init__(
        self,
        store: DigestSchedulerStore,
        dispatcher: NotificationDispatcher,
        clock: Clock,
    ) -> None:
        self._store, self._dispatcher, self._clock = store, dispatcher, clock

    async def run(self) -> None:
        while True:
            try:
                await self._store.enqueue_due(self._clock.now())
                await self._dispatcher.tick()
            except Exception:
                log.warning("notification_digest_tick_failed")
            await asyncio.sleep(30)
