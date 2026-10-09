"""Human activity, rather than token rotation, controls the session idle deadline."""

from datetime import timedelta

import pytest
from pydantic import ValidationError

from ase.infrastructure.settings import Settings
from helpers import USER_EMAIL, USER_PASSWORD, bearer, csrf_headers, login


async def test_passive_refresh_cannot_extend_idle_deadline(client, user, clock):
    await login(client, USER_EMAIL, USER_PASSWORD)
    clock.advance(timedelta(minutes=179))
    refreshed = await client.post("/api/auth/refresh", headers=csrf_headers(client))
    assert refreshed.status_code == 200
    clock.advance(timedelta(minutes=1))
    expired = await client.post("/api/auth/refresh", headers=csrf_headers(client))
    assert expired.status_code == 401
    assert expired.json()["error"]["code"] == "session_idle_expired"


async def test_activity_is_csrf_protected_and_rate_limited(client, user, clock):
    signed_in = await login(client, USER_EMAIL, USER_PASSWORD)
    headers = bearer(signed_in.json()["access_token"])
    assert (await client.post("/api/auth/activity", headers=headers)).status_code == 403
    headers.update(csrf_headers(client))
    assert (await client.post("/api/auth/activity", headers=headers)).status_code == 429
    clock.advance(timedelta(minutes=1))
    active = await client.post("/api/auth/activity", headers=headers)
    assert active.status_code == 200
    assert active.json()["last_activity_at"] == clock.now().isoformat().replace("+00:00", "Z")
    assert (await client.post("/api/auth/activity", headers=headers)).status_code == 429


@pytest.mark.parametrize("marker,expected", [("1", 200), ("0", 401), ("true", 401)])
async def test_only_explicit_activity_refresh_moves_deadline(client, user, clock, marker, expected):
    await login(client, USER_EMAIL, USER_PASSWORD)
    clock.advance(timedelta(minutes=179))
    headers = {**csrf_headers(client), "x-ase-activity": marker}
    assert (await client.post("/api/auth/refresh", headers=headers)).status_code == 200
    clock.advance(timedelta(minutes=1))
    assert (
        await client.post("/api/auth/refresh", headers=csrf_headers(client))
    ).status_code == expected


async def test_refresh_marker_and_heartbeat_share_one_persistent_minute_budget(client, user, clock):
    signed_in = await login(client, USER_EMAIL, USER_PASSWORD)
    clock.advance(timedelta(seconds=60))
    refreshed = await client.post(
        "/api/auth/refresh", headers={**csrf_headers(client), "x-ase-activity": "1"}
    )
    activity = refreshed.json()["activity"]
    clock.advance(timedelta(seconds=59))
    headers = {**bearer(signed_in.json()["access_token"]), **csrf_headers(client)}
    denied = await client.post("/api/auth/activity", headers=headers)
    assert denied.status_code == 429 and denied.headers["retry-after"] == "1"
    passive = await client.post("/api/auth/refresh", headers=csrf_headers(client))
    assert passive.json()["activity"]["last_activity_at"] == activity["last_activity_at"]
    clock.advance(timedelta(seconds=1))
    allowed = await client.post("/api/auth/activity", headers={**headers, **csrf_headers(client)})
    assert allowed.status_code == 200


@pytest.mark.parametrize("field", ["session_idle_minutes", "admin_session_idle_minutes"])
@pytest.mark.parametrize("minutes,valid", [(4, False), (5, True), (1440, True), (1441, False)])
def test_idle_configuration_bounds(field, minutes, valid):
    values = {field: minutes, "_env_file": None}
    if valid:
        assert getattr(Settings(**values), field) == minutes
    else:
        with pytest.raises(ValidationError):
            Settings(**values)
