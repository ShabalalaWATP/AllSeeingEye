"""Independent SQLite/PostgreSQL connections never own one external delivery together."""

import asyncio
import os

import pytest

from ase.application.account.notification_dispatch import NotificationDispatcher
from test_notification_delivery import Sender, _enqueue, _rows, setup_delivery


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
