"""Opt-in monitoring HTTP lifecycle is scoped, bounded and snapshot-free on input."""

import json
from dataclasses import asdict
from uuid import UUID

import pytest

from annotation_comparison_helpers import prepared
from annotation_monitor_helpers import correct, seeded
from helpers import USER_PASSWORD, bearer, login_token
from test_annotation_monitoring import tick


async def test_create_observe_exact_download_pause_policy_and_delete(client, container, user):
    actor, report, _, claim, request = await prepared(client, container, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    body = {
        "name": "Selected claim",
        "selection": json.loads(json.dumps(asdict(request.before), default=str)),
        "categories": ["claim"],
        "notify_on_change": True,
    }
    result = await client.post("/api/annotation-monitors", headers=headers, json=body)
    assert result.status_code == 200, result.text
    monitor = result.json()
    path = f"/api/annotation-monitors/{monitor['id']}"
    assert monitor["checkpoint_number"] == 0 and monitor["selection"] == body["selection"]
    assert (await client.get("/api/annotation-monitors", headers=headers)).json()["total"] == 1
    corrected = await correct(container, actor, claim)
    assert await tick(container, UUID(monitor["id"]))
    history = await client.get(f"{path}/transitions", headers=headers)
    transition = history.json()["items"][0]
    detail = await client.get(f"{path}/transitions/{transition['id']}", headers=headers)
    assert detail.status_code == 200, detail.text
    assert detail.json()["comparison"]["after"]["revisions"][0]["id"] == str(corrected.id)
    export_path = f"{path}/transitions/{transition['id']}/export"
    exported = await client.post(
        export_path,
        headers=headers,
        json={"expected_comparison_sha256": transition["comparison_sha256"]},
    )
    assert exported.status_code == 200 and exported.json()["transition"]["id"] == transition["id"]
    assert exported.headers["cache-control"] == "private, no-store"
    stale = await client.post(
        export_path, headers=headers, json={"expected_comparison_sha256": "0" * 64}
    )
    assert stale.status_code == 409
    current = (await client.get(path, headers=headers)).json()
    assert (
        await client.delete(path, headers=headers, params={"expected_revision": 1})
    ).status_code == 409
    assert (
        await client.delete(
            path, headers=headers, params={"expected_revision": current["revision"]}
        )
    ).status_code == 204
    assert (await client.get(path, headers=headers)).status_code == 404
    async with container.session_factory() as session:
        assert await container.repositories(session).reports.get(report.id) is not None


@pytest.mark.parametrize("fault", ["empty", "kind", "actor", "history", "categories", "policy"])
async def test_input_cannot_forge_monitor_scope_or_immutable_history(
    client, container, user, fault
):
    _, _, _, _, request = await prepared(client, container, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    body = {
        "name": "Selected claim",
        "selection": json.loads(json.dumps(asdict(request.before), default=str)),
        "categories": ["claim"],
    }
    if fault == "empty":
        body["selection"]["revisions"] = []
    elif fault == "kind":
        body["categories"] = ["confidence"]
    elif fault == "actor":
        body["created_by"] = str(user.id)
    elif fault == "history":
        body["checkpoint_payload"] = {}
    elif fault == "categories":
        body["categories"] = ["identity"]
    else:
        body["categories"] = ["claim", "claim"]
    result = await client.post("/api/annotation-monitors", headers=headers, json=body)
    assert result.status_code == 422, result.text


async def test_other_person_cannot_list_read_or_delete_private_monitor(
    client, container, user, admin
):
    _, _, _, _, monitor = await seeded(client, container, admin)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    path = f"/api/annotation-monitors/{monitor.id}"
    assert (await client.get("/api/annotation-monitors", headers=headers)).json()["items"] == []
    assert (await client.get(path, headers=headers)).status_code == 404
    assert (
        await client.delete(path, headers=headers, params={"expected_revision": 1})
    ).status_code == 404
