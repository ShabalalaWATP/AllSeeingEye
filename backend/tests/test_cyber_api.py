"""Cyber endpoints recheck current source and session authority before releasing data."""

from dataclasses import replace
from datetime import timedelta

import pytest

from ase.adapters.persistence.source_controls import SqlSourceControlRepository
from ase.adapters.persistence.users import SqlUserRepository
from ase.domain.events import Category
from feeds_helpers import make_event
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token


async def disable(container, source_id, user_id):
    async with container.source_admission.guard(), container.session_factory() as session:
        await SqlSourceControlRepository(session).set(
            source_id, False, container.clock.now(), user_id
        )
        await session.commit()


async def test_authentication_no_store_and_reference_catalogue(client, user, container):
    for path in ("/api/cyber", "/api/cyber/actors"):
        assert (await client.get(path)).status_code == 401
    assert (await client.post("/api/cyber/briefing")).status_code == 401
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    response = await client.get("/api/cyber", headers=headers)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "private, no-store"
    assert response.json()["window_days"] == 2
    assert len(response.json()["sources"]) == 19
    assert all(row["status"] == "idle" for row in response.json()["sources"])
    assert [row["theme"] for row in response.json()["themes"]] == [
        "nation_state",
        "nato_allies",
        "uk_infrastructure",
        "ukraine",
        "gnss_interference",
        "critical_infrastructure",
    ]
    assert response.json()["state_mentions"] == []
    references = await client.get("/api/cyber/actors", headers=headers)
    assert references.status_code == 200, references.text
    assert references.headers["cache-control"] == "private, no-store"
    catalogue = references.json()["catalogue"]
    assert references.json()["available"] and catalogue["version"] == "19.2"
    assert len(catalogue["actors"]) == 176
    assert catalogue["actors"][0]["technique_count"] == len(catalogue["actors"][0]["technique_ids"])
    by_id = {actor["group_id"]: actor for actor in catalogue["actors"]}
    assert by_id["G0007"]["state_association"] == "Russia"
    assert by_id["G0046"]["state_association"] is None
    await disable(container, "mitre_attack", user.id)
    disabled = (await client.get("/api/cyber/actors", headers=headers)).json()
    assert disabled["available"] is False and disabled["catalogue"] is None


async def test_source_disabled_after_read_cannot_leak_counts_health_or_records(
    client, user, container, monkeypatch
):
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    now = container.clock.now()
    container.store.upsert(
        (
            make_event(
                "claim",
                source_id="ransomware_live",
                category=Category.CYBER,
                subtype="ransomware",
                title="APT28 claimed incident",
                country_iso="GB",
                published_at=now - timedelta(hours=1),
            ),
        )
    )
    original = container.cyber.read

    async def read_then_disable(*args):
        result = await original(*args)
        assert result.events
        await disable(container, "ransomware_live", user.id)
        return result

    monkeypatch.setattr(container.cyber, "read", read_then_disable)
    response = await client.get("/api/cyber", headers=headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["retained_count"] == 0 and payload["items"] == []
    assert payload["top_countries"] == [] and payload["actor_mentions"] == []
    assert all(row["count"] == 0 for row in payload["counts"])
    assert all(row["source_id"] != "ransomware_live" for row in payload["sources"])


@pytest.mark.parametrize("value", ["1", "3", "15", "true", "tomorrow"])
async def test_endpoint_windows_reject_invalid_values(client, user, value):
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    assert (await client.get(f"/api/cyber?days={value}", headers=headers)).status_code == 422
    assert (
        await client.post(f"/api/cyber/briefing?days={value}", headers=headers)
    ).status_code == 422


async def test_reference_source_is_controlled_but_never_polled(container):
    assert any(spec.id == "mitre_attack" for spec in container.research_sources)
    assert all(connector.spec.id != "mitre_attack" for connector in container.connectors)


async def test_user_revoked_during_preparation_cannot_receive_snapshot(
    client, user, container, monkeypatch
):
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    original = container.cyber.read

    async def read_then_revoke(*args):
        result = await original(*args)
        async with container.session_factory() as session:
            await SqlUserRepository(session).save(replace(user, is_active=False))
            await session.commit()
        return result

    monkeypatch.setattr(container.cyber, "read", read_then_revoke)
    assert (await client.get("/api/cyber", headers=headers)).status_code == 401
