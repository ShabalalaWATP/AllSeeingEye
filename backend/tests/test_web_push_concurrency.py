"""Independent workers share one per-device alert receipt and one external claim."""

import asyncio
import os

import pytest
from sqlalchemy import select

from ase.adapters.persistence.web_push_models import PushDeliveryRow
from test_private_feed import _alert
from test_web_push import (
    Sender,
    configured,  # noqa: F401
    register,
    worker,
)

pytestmark = pytest.mark.usefixtures("configured")


@pytest.fixture(params=["sqlite", "postgres"])
def settings(settings, tmp_path, request):
    if request.param == "postgres":
        url = os.environ.get("ASE_NOTIFICATION_POSTGRES_URL")
        if not url:
            pytest.skip("Set ASE_NOTIFICATION_POSTGRES_URL to a dedicated disposable database.")
    else:
        url = f"sqlite+aiosqlite:///{tmp_path / 'push-races.db'}"
    return settings.model_copy(update={"database_url": url})


async def test_competing_admission_and_delivery_use_one_intent(client, container, user):
    await register(client, container)
    await _alert(container, user)
    sender = Sender()
    runners = [worker(container, sender)[0] for _ in range(4)]
    await asyncio.gather(*(runner.tick() for runner in runners))
    assert len(sender.messages) == 1
    async with container.session_factory() as session:
        rows = list(await session.scalars(select(PushDeliveryRow)))
        assert len(rows) == 1 and rows[0].state == "sent"
