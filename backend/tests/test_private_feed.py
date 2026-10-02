"""Narrow feed credentials are opt-in, revocable and never grant account API access."""

from base64 import b64encode
from uuid import uuid4

import pytest
from defusedxml.ElementTree import fromstring
from httpx import AsyncClient
from sqlalchemy import select

from ase.adapters.persistence.notification_models import PrivateFeedTokenRow
from ase.adapters.persistence.operational_models import AlertRow
from ase.container import Container
from ase.domain.users import User
from helpers import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    USER_EMAIL,
    USER_PASSWORD,
    bearer,
    login_token,
)

PATH = "/api/me/notifications/feed"
ATOM = "/api/notifications/feed.atom"


def feed_auth(token: str) -> dict[str, str]:
    value = b64encode(f"feed:{token}".encode()).decode()
    return {"Authorization": f"Basic {value}"}


async def _alert(container: Container, owner: User, *, title: str = "Private alert") -> None:
    async with container.session_factory() as session:
        session.add(
            AlertRow(
                id=uuid4(),
                indicator_id=uuid4(),
                schedule_id=None,
                created_by=owner.id,
                team_id=None,
                fired_at=container.clock.now(),
                title=title,
                summary="SECRET evidence and report prose",
                count=1,
                threshold=1,
                event_ids=["secret-event"],
                countries=["GB"],
            )
        )
        await session.commit()


async def test_feed_default_rotation_revoke_and_hashed_storage(
    client: AsyncClient,
    container: Container,
    user: User,
) -> None:
    session = await login_token(client, USER_EMAIL, USER_PASSWORD)
    headers = bearer(session)
    response = await client.get(PATH, headers=headers)
    assert response.json() == {"enabled": False, "include_titles": False, "created_at": None}
    assert (await client.get(ATOM)).status_code == 401
    assert (await client.post(PATH, json={})).status_code == 401
    enabled = await client.post(PATH, headers=headers, json={})
    assert enabled.status_code == 200, enabled.text
    token = enabled.json()["token"]
    assert token not in enabled.json()["feed_url"]
    async with container.session_factory() as db:
        stored = await db.scalar(select(PrivateFeedTokenRow))
        assert stored is not None
        assert stored.token_hash == container.generator.hash(token)
        assert stored.token_hash != token
    assert "token" not in (await client.get(PATH, headers=headers)).json()
    # A feed token is not an access JWT and cannot read reports or manage settings.
    assert (await client.get("/api/me", headers=bearer(token))).status_code == 401
    fresh = await client.post(PATH, headers=headers, json={"include_titles": True})
    assert (await client.get(ATOM, headers=feed_auth(token))).status_code == 401
    fresh_token = fresh.json()["token"]
    assert (await client.get(ATOM, headers=feed_auth(fresh_token))).status_code == 200
    assert (await client.delete(PATH, headers=headers)).status_code == 204
    assert (await client.get(ATOM, headers=feed_auth(fresh_token))).status_code == 401


@pytest.mark.parametrize("change", ["deactivate", "security_version"])
async def test_account_changes_immediately_invalidate_feed(
    client: AsyncClient,
    container: Container,
    user: User,
    change: str,
) -> None:
    session = await login_token(client, USER_EMAIL, USER_PASSWORD)
    issued = await client.post(PATH, headers=bearer(session), json={})
    token = issued.json()["token"]
    async with container.session_factory() as db:
        repos = container.repositories(db)
        current = await repos.users.lock_by_id(user.id)
        assert current is not None
        if change == "deactivate":
            current.is_active = False
        else:
            current.security_version += 1
        await repos.users.save(current)
        await repos.uow.commit()
    assert (await client.get(ATOM, headers=feed_auth(token))).status_code == 401


@pytest.mark.parametrize("titles", [False, True])
async def test_scope_minimisation_and_xml_escaping(
    client: AsyncClient,
    container: Container,
    user: User,
    admin: User,
    titles: bool,
) -> None:
    await _alert(container, user, title="<img src=x onerror=evil> & private")
    await _alert(container, admin, title="Other owner")
    session = await login_token(client, USER_EMAIL, USER_PASSWORD)
    issued = await client.post(PATH, headers=bearer(session), json={"include_titles": titles})
    result = await client.get(ATOM, headers=feed_auth(issued.json()["token"]))
    assert result.status_code == 200, result.text
    assert result.headers["cache-control"] == "private, no-store"
    assert result.headers["referrer-policy"] == "no-referrer"
    assert result.headers["content-type"].startswith("application/atom+xml")
    assert "SECRET" not in result.text and "secret-event" not in result.text
    assert "Other owner" not in result.text and "<img" not in result.text
    entries = fromstring(result.content).findall("{http://www.w3.org/2005/Atom}entry")
    assert len(entries) == 1
    title = entries[0].findtext("{http://www.w3.org/2005/Atom}title")
    assert title == ("<img src=x onerror=evil> & private" if titles else "Alert")
    admin_session = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    own_feed = await client.post(PATH, headers=bearer(admin_session), json={"include_titles": True})
    admin_result = await client.get(ATOM, headers=feed_auth(own_feed.json()["token"]))
    assert "Other owner" in admin_result.text
    assert "onerror" not in admin_result.text


async def test_feed_rate_limit_and_bounded_history(
    client: AsyncClient,
    container: Container,
    user: User,
) -> None:
    session = await login_token(client, USER_EMAIL, USER_PASSWORD)
    issued = await client.post(PATH, headers=bearer(session), json={})
    headers = feed_auth(issued.json()["token"])
    for _ in range(101):
        await _alert(container, user)
    result = await client.get(ATOM, headers=headers)
    assert result.status_code == 200
    assert result.text.count("<entry>") == 100
    assert "older entries are omitted" in result.text
    for _ in range(11):
        assert (await client.get(ATOM, headers=headers)).status_code == 200
    assert (await client.get(ATOM, headers=headers)).status_code == 429


async def test_feed_survives_session_logout_but_not_token_revocation(
    client: AsyncClient,
    user: User,
) -> None:
    session = await login_token(client, USER_EMAIL, USER_PASSWORD)
    issued = await client.post(PATH, headers=bearer(session), json={})
    headers = feed_auth(issued.json()["token"])
    # A feed is an explicitly independent read-only credential, not a session JWT.
    response = await client.post("/api/me/sessions/revoke-others", headers=bearer(session))
    assert response.status_code == 204
    assert (await client.get(ATOM, headers=headers)).status_code == 200
