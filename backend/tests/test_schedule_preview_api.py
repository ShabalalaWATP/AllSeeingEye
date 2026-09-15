"""Subscription preview shows actual local/UTC slots without creating work."""

from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token


async def test_preview_is_authorised_and_read_only(client, user) -> None:
    body = {
        "name": "Daily Ukraine update",
        "template_id": "intsum",
        "country_iso": "UA",
        "timezone": "Europe/London",
        "local_hour": 8,
        "local_minute": 30,
        "collection_policy": "rolling_snapshot",
    }
    assert (await client.post("/api/schedules/preview", json=body)).status_code == 401
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    result = await client.post("/api/schedules/preview", json=body, headers=bearer(token))
    assert result.status_code == 200, result.text
    assert result.headers["Cache-Control"] == "private, no-store"
    assert len(result.json()["next_three"]) == 3
    assert all(item["local"] and item["utc"] for item in result.json()["next_three"])
    schedules = await client.get("/api/schedules", headers=bearer(token))
    assert schedules.status_code == 200 and schedules.json()["items"] == []
    invalid = await client.post(
        "/api/schedules/preview",
        json={**body, "timezone": "Not/AZone"},
        headers=bearer(token),
    )
    assert invalid.status_code == 422
