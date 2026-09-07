"""Identity HTTP contracts, immutable history and server-owned anchors."""

from uuid import uuid4

import pytest

from helpers import USER_PASSWORD, bearer, login_token
from test_report_identity_service import seed_report


def body(record):
    return {
        "report_id": str(record.id),
        "version_number": 1,
        "candidate_label": "E1",
        "disposition": "unresolved",
        "rationale": "Registration needs corroboration.",
    }


async def test_create_history_correction_and_version_listing(client, container, user):
    record, version = await seed_report(container, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    payload = body(record)
    response = await client.post("/api/identity-reviews", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    assert response.headers["cache-control"] == "no-store"
    first = response.json()
    assert first["subject"] == record.scope["research_subject"]
    assert first["report_version_id"] == str(version.id)
    assert first["authored_by"] == str(user.id)
    path = f"/api/identity-reviews/{first['decision_id']}"
    patch = {
        key: value for key, value in payload.items() if key not in {"report_id", "version_number"}
    }
    patch.update(base_revision_id=first["id"], disposition="rejected")
    second = await client.patch(path, headers=headers, json=patch)
    assert second.status_code == 200, second.text
    assert second.json()["number"] == 2
    assert (await client.patch(path, headers=headers, json=patch)).status_code == 409
    old = await client.get(f"{path}/revisions/{first['id']}", headers=headers)
    assert old.status_code == 200 and old.json()["revision"] == first
    current = await client.get(path, headers=headers)
    assert current.json()["revision"] == second.json()
    assert (await client.get(f"{path}/revisions/{uuid4()}", headers=headers)).status_code == 404
    page = await client.get(
        "/api/identity-reviews",
        headers=headers,
        params={"report_id": str(record.id), "version_number": 1},
    )
    assert page.status_code == 200 and page.json()["items"] == [second.json()]
    assert page.json()["total"] == 1 and page.headers["cache-control"] == "no-store"
    assert (
        await client.post("/api/identity-reviews", headers=headers, json=payload)
    ).status_code == 409


@pytest.mark.parametrize(
    "field,value",
    [
        ("subject", "Choose my own subject"),
        ("authored_by", str(uuid4())),
        ("team_id", str(uuid4())),
        ("candidate", {}),
        ("version_number", True),
        ("version_number", "1"),
        ("version_number", 0),
        ("rationale", ""),
        ("disposition", "certain"),
        ("citations", [{}]),
    ],
)
async def test_boundary_rejects_client_owned_anchors_and_invalid_values(
    client, container, user, field, value
):
    record, _ = await seed_report(container, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    response = await client.post(
        "/api/identity-reviews", headers=headers, json={**body(record), field: value}
    )
    assert response.status_code == 422, response.text


async def test_citation_must_match_frozen_excerpt(client, container, user):
    record, version = await seed_report(container, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    item = version.evidence[0]
    payload = {
        **body(record),
        "citations": [
            {
                "label": item.label,
                "relation": "supporting",
                "field": "title",
                "start": 0,
                "end": len(item.title),
                "text": "invented text",
            }
        ],
    }
    response = await client.post("/api/identity-reviews", headers=headers, json=payload)
    assert response.status_code == 422, response.text
    payload["citations"][0]["text"] = item.title
    response = await client.post("/api/identity-reviews", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    assert response.json()["citations"][0]["excerpt"]["text"] == item.title


async def test_authentication_and_page_bounds(client, container, user):
    record, _ = await seed_report(container, user)
    assert (await client.post("/api/identity-reviews", json=body(record))).status_code == 401
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    for params in ({"limit": 21}, {"offset": -1}, {"offset": 1001}):
        response = await client.get(
            "/api/identity-reviews",
            headers=headers,
            params={"report_id": str(record.id), "version_number": 1, **params},
        )
        assert response.status_code == 422
