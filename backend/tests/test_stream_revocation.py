"""An open stream must stop before emitting data after its session is revoked."""

import asyncio
import json

import pytest
from httpx import AsyncClient

from ase.api.routers import stream as stream_router
from ase.application.ports.feeds import BusMessage
from ase.container import Container
from ase.domain.users import User
from helpers import USER_EMAIL, USER_PASSWORD, csrf_headers, login_token


@pytest.mark.parametrize("message_arrives", [True, False])
async def test_open_stream_rechecks_session_on_data_and_idle_heartbeat(
    client: AsyncClient,
    container: Container,
    user: User,
    monkeypatch,
    message_arrives: bool,
) -> None:
    monkeypatch.setattr(stream_router, "PING_SECONDS", 0.01)
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    response = await stream_router.stream(user, container.issuer.verify(token), container)
    iterator = response.body_iterator
    try:
        assert (await anext(iterator))["event"] == "hello"
        logout = await client.post("/api/auth/logout", headers=csrf_headers(client))
        assert logout.status_code == 204
        if message_arrives:
            await container.bus.publish(BusMessage("event.expire", {"ids": ["private"]}))
        async with asyncio.timeout(2):
            packet = await anext(iterator)
        assert packet["event"] == "bye"
        assert json.loads(packet["data"]) == {"reason": "session_revoked"}
    finally:
        await iterator.aclose()
    assert container.streams.held(user.id) == 0
