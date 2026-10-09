"""Optional push wiring, with all external delivery disabled unless keys are configured."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.web_push_delivery import SqlPushDeliveryStore
from ase.adapters.persistence.web_push_devices import SqlPushDevices
from ase.application.account.web_push import WebPushService, WebPushWorker

if TYPE_CHECKING:
    from ase.adapters.notify.web_push import WebPushSender
    from ase.container import Container


def push_sender(container: Container) -> WebPushSender | None:
    key, subject = (
        container.settings.web_push_vapid_private_key,
        container.settings.web_push_vapid_subject,
    )
    if key is None or subject is None or not container.cipher.available:
        return None
    # Unconfigured workers must not load the optional delivery libraries.
    from ase.adapters.notify.web_push import WebPushSender  # noqa: PLC0415

    return WebPushSender(key.get_secret_value(), subject)


def web_push_service(container: Container, session: AsyncSession) -> WebPushService:
    # Resolve the real validator when a push API service is requested.
    from ase.adapters.notify.web_push import WebPushValidator  # noqa: PLC0415

    repos = container.repositories(session)
    return WebPushService(
        SqlPushDevices(session, container.cipher),
        WebPushValidator(),
        container.access_policy(session),
        repos.users,
        repos.refresh_tokens,
        container.clock,
        repos.uow,
        push_sender(container) is not None,
        container.limiter,
    )


async def run_web_push(container: Container) -> None:
    sender = push_sender(container)
    if sender is None:
        # No source querying, outbox admission or transport in an unconfigured installation.
        await asyncio.Event().wait()
        return
    await WebPushWorker(
        SqlPushDeliveryStore(
            container.session_factory,
            container.access_policy,
            container.cipher,
            lambda session: container.repositories(session).refresh_tokens,
        ),
        sender,
        container.clock,
    ).run()
