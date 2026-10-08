"""A `since` query value without a UTC offset is read as UTC instead of failing with 500."""

from __future__ import annotations

from datetime import timedelta

from httpx import AsyncClient

from ase.container import Container
from ase.domain.events import Category
from ase.domain.users import User
from feeds_helpers import NOW, make_event
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token


async def test_events_since_without_an_offset_is_read_as_utc(
    client: AsyncClient, container: Container, user: User
) -> None:
    container.store.upsert([make_event("q"), make_event("k", category=Category.CYBER)])
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)

    async def count(since: str) -> int:
        response = await client.get("/api/events", params={"since": since}, headers=bearer(token))
        assert response.status_code == 200, response.text
        return int(response.json()["count"])

    naive = NOW.replace(tzinfo=None)
    assert await count((naive - timedelta(minutes=1)).isoformat()) == 2
    assert await count((naive + timedelta(minutes=1)).isoformat()) == 0
    # Two hours ahead of UTC: one minute after NOW in UTC, so it excludes both items.
    assert await count((naive + timedelta(hours=2, minutes=1)).isoformat() + "+02:00") == 0
    assert await count((naive + timedelta(hours=2, minutes=-1)).isoformat() + "+02:00") == 2
