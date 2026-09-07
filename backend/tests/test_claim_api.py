"""Claim HTTP history, frozen-version listing and strict boundary validation."""

from dataclasses import replace
from uuid import uuid4

import pytest

from helpers import USER_PASSWORD, bearer, login_token
from test_claim_repository import seed


def body(report, version):
    item = version.evidence[0]
    return {
        "report_id": str(report.id),
        "version_number": 1,
        "statement": "The source reports the observation.",
        "kind": "reported_fact",
        "state": "proposed",
        "reason": "Capture for review.",
        "citations": [
            {
                "label": item.label,
                "relation": "supporting",
                "field": "title",
                "start": 0,
                "end": len(item.title),
                "text": item.title,
            }
        ],
    }


async def test_exact_history_stale_edit_and_bounded_list(client, container, user):
    report, version, _ = await seed(container, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    payload = body(report, version)
    response = await client.post("/api/claims", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    assert response.headers["cache-control"] == "no-store"
    first = response.json()
    path = f"/api/claims/{first['claim_id']}"
    patch = {
        key: value for key, value in payload.items() if key not in {"report_id", "version_number"}
    }
    patch.update(base_revision_id=first["id"], state="reviewed", reason="Checked attribution.")
    updated = await client.patch(path, headers=headers, json=patch)
    assert updated.status_code == 200, updated.text
    assert updated.json()["number"] == 2
    assert (await client.patch(path, headers=headers, json=patch)).status_code == 409
    old = await client.get(f"{path}/revisions/{first['id']}", headers=headers)
    assert old.status_code == 200 and old.json()["revision"] == first
    current = await client.get(path, headers=headers)
    assert current.json()["revision"] == updated.json()
    page = await client.get(
        f"/api/claims?report_id={report.id}&version_number=1&limit=1", headers=headers
    )
    assert page.status_code == 200, page.text
    assert page.json()["total"] == 2 and len(page.json()["items"]) == 1
    assert page.headers["cache-control"] == "no-store"
    assert (
        await client.get(
            f"/api/claims?report_id={report.id}&version_number=1&limit=21", headers=headers
        )
    ).status_code == 422


@pytest.mark.parametrize("change", ["actor", "bool", "empty", "wrong_text"])
async def test_invalid_claim_boundary(client, container, user, change):
    report, version, _ = await seed(container, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    payload = body(report, version)
    if change == "actor":
        payload["authored_by"] = str(uuid4())
    elif change == "bool":
        payload["citations"][0]["start"] = False
    elif change == "empty":
        payload["citations"] = []
    else:
        payload["citations"][0]["text"] = "Uncaptured assertion"
    response = await client.post("/api/claims", headers=headers, json=payload)
    assert response.status_code in (400, 422), response.text


async def test_foreign_claim_list_and_history_are_hidden(client, container, user):
    report, _, first = await seed(container, replace(user, id=uuid4()))
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    for path in [
        f"/api/claims/{first.claim_id}",
        f"/api/claims/{first.claim_id}/revisions/{first.id}",
        f"/api/claims?report_id={report.id}&version_number=1",
    ]:
        assert (await client.get(path, headers=headers)).status_code == 404


async def test_oversized_version_is_rejected_before_database_binding(client, container, user):
    report, version, _ = await seed(container, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    payload = {**body(report, version), "version_number": 9223372036854775808}
    assert (await client.post("/api/claims", headers=headers, json=payload)).status_code == 422
    response = await client.get(
        f"/api/claims?report_id={report.id}&version_number=9223372036854775808", headers=headers
    )
    assert response.status_code == 422
