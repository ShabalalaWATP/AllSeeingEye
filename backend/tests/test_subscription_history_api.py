"""Edition history is bounded, scoped and linked to the durable queue."""

from datetime import timedelta

from httpx import AsyncClient

from ase.container import Container
from ase.domain.users import User
from helpers import USER_EMAIL, USER_PASSWORD, bearer, create_user, login_token
from llm_fixture_helpers import seed_legacy_profile
from report_helpers import PROFILE


async def test_edition_history_is_paginated_and_scope_checked(
    client: AsyncClient, container: Container, user: User
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    second_user = await create_user(
        container, email="edition-reader@example.com", password="another-long-passphrase"
    )
    second_token = await login_token(client, second_user.email, "another-long-passphrase")
    await seed_legacy_profile(container, {**PROFILE, "roles": ["assessment"]})
    now = container.clock.now()
    response = await client.post(
        "/api/schedules",
        json={
            "name": "History test",
            "template_id": "intsum",
            "country_iso": "UA",
            "hour_utc": (now.hour + 1) % 24,
        },
        headers=bearer(token),
    )
    assert response.status_code == 201, response.text
    schedule_id = response.json()["id"]
    endpoint = f"/api/schedules/{schedule_id}/editions"

    assert (await client.get(endpoint, headers=bearer(second_token))).status_code == 404
    assert (await client.get(endpoint, headers=bearer(token))).json()["items"] == []
    assert (await client.get(endpoint + "?limit=101", headers=bearer(token))).status_code == 422
    assert (await client.get(endpoint + "?offset=-1", headers=bearer(token))).status_code == 422

    container.clock.advance(timedelta(hours=2))
    assert await container.schedule_runner.run_once() == 1
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    history = await client.get(endpoint + "?limit=1&offset=0", headers=bearer(token))
    assert history.status_code == 200, history.text
    body = history.json()
    assert body["limit"] == 1 and body["offset"] == 0
    assert len(body["items"]) == 1
    edition = body["items"][0]
    assert edition["subscription_id"] == schedule_id
    assert edition["workflow"] == "queued"
    assert edition["job_id"] and edition["report_id"] is None
    assert edition["comparison"] is None
    assert edition["requested"]["start"] < edition["requested"]["end"]
    assert (await client.get(endpoint + "?limit=1&offset=1", headers=bearer(token))).json()[
        "items"
    ] == []
