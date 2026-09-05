"""Deep model JSON degrades each caller safely instead of escaping into an API failure."""

from __future__ import annotations

import json

import httpx

from ase.application.ports.feeds import EventQuery
from ase.container import Container
from ase.domain.users import User
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, USER_EMAIL, USER_PASSWORD, bearer, login_token
from report_helpers import PROFILE, ScriptedGateway, filled_store, good_body


def nested_output() -> str:
    # CPython 3.13 has a separate C decoder depth limit above sys.getrecursionlimit().
    depth = 10_000
    return "[" * depth + '"untrusted-output-marker"' + "]" * depth


async def test_report_retries_and_records_safe_deep_json_failure(
    client: httpx.AsyncClient, container: Container, admin: User, user: User
) -> None:
    admin_token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    user_token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    await client.post("/api/admin/llm/profiles", json=PROFILE, headers=bearer(admin_token))
    container.llm = ScriptedGateway(nested_output(), nested_output())
    response = await client.post(
        "/api/reports", json={"template": "intsum"}, headers=bearer(user_token)
    )
    assert response.status_code == 201
    result = response.json()
    assert result["report"]["status"] == "failed" and result["version"]["attempts"] == 2
    assert result["version"]["findings"][0]["message"] == "Model JSON is nested too deeply."
    stored = await client.get(f"/api/reports/{result['report']['id']}", headers=bearer(user_token))
    usage = await client.get("/api/admin/llm/usage", headers=bearer(admin_token))
    for record in (response, stored, usage):
        assert "untrusted-output-marker" not in record.text
        assert "nested too deeply" in record.text


async def test_direction_and_advocacy_degrade_without_losing_the_report(
    client: httpx.AsyncClient, container: Container, admin: User, user: User
) -> None:
    admin_token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    user_token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    profile = {**PROFILE, "roles": ["assessment", "direction", "devil"]}
    await client.post("/api/admin/llm/profiles", json=profile, headers=bearer(admin_token))
    container.store.upsert(list(filled_store().query(EventQuery(limit=10))))
    container.llm = ScriptedGateway(nested_output(), json.dumps(good_body()), nested_output())
    response = await client.post(
        "/api/reports",
        json={"template": "ask", "question": "What is changing?", "devils_advocacy": True},
        headers=bearer(user_token),
    )
    assert response.status_code == 201
    version = response.json()["version"]
    assert version["status"] == "ready"
    assert version["direction"] is None and version["devils_advocacy"] is None
    findings = [finding["message"] for finding in version["findings"]]
    assert "Direction JSON is nested too deeply." in findings
    assert "Advocacy JSON is nested too deeply." in findings
    assert "untrusted-output-marker" not in response.text


async def test_admin_connection_check_handles_deep_model_json(
    client: httpx.AsyncClient, container: Container, admin: User
) -> None:
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    created = await client.post("/api/admin/llm/profiles", json=PROFILE, headers=bearer(token))
    container.llm = ScriptedGateway(nested_output())
    response = await client.post(
        f"/api/admin/llm/profiles/{created.json()['id']}/test", headers=bearer(token)
    )
    assert response.status_code == 200
    assert response.json()["ok"] is False
    assert response.json()["error"] == "The model did not answer with JSON."
    usage = await client.get("/api/admin/llm/usage", headers=bearer(token))
    assert usage.json()["items"][0]["ok"] is False
    assert "untrusted-output-marker" not in response.text + usage.text
