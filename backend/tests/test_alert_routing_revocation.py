"""Queued rule exports require fresh authority for both router and endpoint registrar."""

import pytest

from alert_routing_helpers import (
    delivery_store,
    destination,
    enable_mail,
    fire,
    outbox,
    rule,
    save_route,
)
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, USER_PASSWORD, bearer, create_user, login_token


@pytest.mark.parametrize("revoked", ["router", "registrar", "team", "rule"])
async def test_team_exports_stop_after_authority_changes(
    client, container, admin, user, monkeypatch, revoked
):
    admin_headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    created = await client.post("/api/teams", headers=admin_headers, json={"name": "Routing desk"})
    team = created.json()["id"]
    registrar = await create_user(container, email="registrar@example.com", password=USER_PASSWORD)
    for person in (user, registrar):
        response = await client.put(
            f"/api/teams/{team}/members",
            headers=admin_headers,
            json={"email": person.email, "role": "manager"},
        )
        assert response.status_code == 200
    headers, rule_id = await rule(client, user, team_id=team)
    registrar_headers = bearer(await login_token(client, registrar.email, USER_PASSWORD))
    target = await destination(client, registrar_headers, monkeypatch, team_id=team)
    await enable_mail(container, user)
    await save_route(client, headers, rule_id, email=revoked != "registrar", webhook=target)
    await fire(container, rule_id)
    if revoked in {"router", "registrar"}:
        person = user if revoked == "router" else registrar
        response = await client.put(
            f"/api/teams/{team}/members",
            headers=admin_headers,
            json={"email": person.email, "role": "member"},
        )
    elif revoked == "team":
        response = await client.patch(
            f"/api/teams/{team}", headers=admin_headers, json={"is_active": False}
        )
    else:
        listed = await client.get("/api/warning/indicators", headers=headers)
        assert listed.status_code == 200
        current = next(item for item in listed.json()["items"] if item["id"] == rule_id)
        response = await client.put(
            f"/api/warning/indicators/{rule_id}",
            headers=headers,
            json={
                "name": "Routing rule",
                "team_id": team,
                "enabled": False,
                "expected_updated_at": current["updated_at"],
            },
        )
    assert response.status_code == 200, response.text
    store = delivery_store(container)
    processed = 0
    while claim := await store.claim(container.clock.now()):
        assert await store.prepare(claim, container.clock.now()) is None
        processed += 1
    assert processed > 0
    assert all(row.state == "cancelled" for row in await outbox(container))
