"""Independent SQLite/PostgreSQL connections never own one external delivery together."""

import asyncio
import os
from datetime import timedelta

import pytest

from ase.application.account.notification_dispatch import NotificationDispatcher
from ase.container.notifications import digest_worker
from test_notification_delivery import Sender, _enqueue, _rows, setup_delivery
from test_notification_digest import _enable
from test_notification_digest import _rows as digest_rows
from test_private_feed import _alert


@pytest.fixture(params=["sqlite", "postgres"])
def settings(settings, tmp_path, request):
    if request.param == "postgres":
        url = os.environ.get("ASE_NOTIFICATION_POSTGRES_URL")
        if not url:
            pytest.skip("Set ASE_NOTIFICATION_POSTGRES_URL to a dedicated disposable database.")
    else:
        url = f"sqlite+aiosqlite:///{tmp_path / 'notification-races.db'}"
    return settings.model_copy(update={"database_url": url})


async def test_competing_enqueue_and_dispatch_have_one_intent_and_one_owner(container, user):
    _, edition, store = await setup_delivery(container, user)
    await asyncio.gather(*(_enqueue(container, edition) for _ in range(4)))
    assert len(await _rows(container)) == 1
    sender = Sender()
    dispatchers = [NotificationDispatcher(store, sender, container.clock) for _ in range(4)]
    await asyncio.gather(*(dispatcher.tick() for dispatcher in dispatchers))
    assert len(sender.messages) == 1
    assert (await _rows(container))[0].state == "sent"


async def test_competing_digest_schedulers_and_senders_preserve_one_window(container, user):
    await _enable(container, user)
    await _alert(container, user)
    container.clock.advance(timedelta(days=1))
    workers = [digest_worker(container) for _ in range(4)]
    await asyncio.gather(*(worker._store.enqueue_due(container.clock.now()) for worker in workers))
    assert len(await digest_rows(container)) == 1
    sender = Sender()
    for worker in workers:
        worker._dispatcher._sender = sender
    await asyncio.gather(*(worker._dispatcher.tick() for worker in workers))
    assert len(sender.messages) == 1
    assert (await digest_rows(container))[0].state == "sent"
