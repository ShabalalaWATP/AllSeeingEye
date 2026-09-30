"""Authenticated opt-in controls do not use administrator inspection rights as consent."""

from httpx import AsyncClient

from ase.adapters.persistence.mfa import SqlMfaRepository
from ase.container import Container
from ase.domain.users import User
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, USER_EMAIL, USER_PASSWORD, bearer, login_token
from test_subscription_editions import _revision


async def test_email_off_unconfigured_and_provisioned_address_requires_confirmation(
    client: AsyncClient,
    container: Container,
    user: User,
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    path = "/api/me/notifications/email"
    result = await client.get(path, headers=bearer(token))
    assert result.json() == {
        "enabled": False,
        "include_names": False,
        "available": False,
        "confirmed": False,
        "destination": USER_EMAIL,
    }
    assert (
        await client.put(path, json={"enabled": True}, headers=bearer(token))
    ).status_code == 422
    async with container.session_factory() as session:
        await SqlMfaRepository(session).set_email_enabled(user.id, True)
        await session.commit()
    assert (
        await client.put(path, json={"enabled": True}, headers=bearer(token))
    ).status_code == 204
    result = await client.get(path, headers=bearer(token))
    assert result.json()["enabled"] is True and result.json()["include_names"] is False
    assert (
        await client.put(path, json={"enabled": False}, headers=bearer(token))
    ).status_code == 204
    assert (await client.put(path, json={"enabled": True})).status_code == 401


async def test_subscription_preferences_are_personal_and_require_current_scope(
    client: AsyncClient,
    container: Container,
    user: User,
    admin: User,
) -> None:
    schedule, _ = await _revision(container, user)
    path = f"/api/schedules/{schedule.id}/notifications/email"
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    other = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    assert (await client.get(path, headers=bearer(token))).json() == {
        "policy": "none",
        "attention": False,
    }
    body = {"policy": "material_changes", "attention": True}
    assert (await client.put(path, headers=bearer(token), json=body)).status_code == 204
    assert (await client.get(path, headers=bearer(token))).json() == body
    assert (await client.get(path, headers=bearer(other))).status_code == 404
    assert (await client.put(path, headers=bearer(other), json=body)).status_code == 404
    invalid = await client.put(
        path, headers=bearer(token), json={"policy": "all", "recipient": str(admin.id)}
    )
    assert invalid.status_code == 422
