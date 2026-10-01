"""A plan-led Research Brief starts durable research only against the reviewed plan revision."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from httpx import AsyncClient

from ase.container import Container
from ase.domain.users import User
from helpers import bearer, create_user, login_token
from report_job_api_helpers import job_settings, prepared, stored
from test_research_brief_api import _draft

__all__ = ["job_settings"]

PLAN = {
    "name": "Border watch",
    "countries": ["UA"],
    "pirs": [
        {
            "text": "Will the crossing close?",
            "sirs": [{"text": "Closures", "keywords": ["closure"]}],
        },
        {"text": "Who is moving?", "sirs": [{"text": "Convoys", "categories": ["conflict"]}]},
    ],
}


async def _plan(client: AsyncClient, headers: dict[str, str], **changes: Any) -> dict[str, Any]:
    response = await client.post("/api/direction/plans", json={**PLAN, **changes}, headers=headers)
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


async def _brief(client: AsyncClient, headers: dict[str, str], plan_id: str) -> str:
    draft = _draft()
    draft["scope"]["plan_id"] = plan_id  # type: ignore[index]
    created = await client.post("/api/research/briefs", json=draft, headers=headers)
    assert created.status_code == 201, created.text
    return str(created.json()["brief"]["identity"]["id"])


async def _start(
    client: AsyncClient, headers: dict[str, str], brief_id: str, expected: str | None
) -> Any:
    body: dict[str, Any] = {"request_id": str(uuid4()), "brief_id": brief_id, "revision": 1}
    if expected is not None:
        body["expected_plan_updated_at"] = expected
    return await client.post("/api/report-jobs/from-brief", json=body, headers=headers)


def _frozen_scope(value: Any) -> dict[str, Any]:
    """The frozen report scope inside a stored job payload, wherever the codec nests it."""
    if isinstance(value, dict):
        if "collection_plan_revision" in value:
            return value
        for item in value.values():
            found = _frozen_scope(item)
            if found:
                return found
    if isinstance(value, list):
        for item in value:
            found = _frozen_scope(item)
            if found:
                return found
    return {}


async def _no_jobs(client: AsyncClient, headers: dict[str, str]) -> None:
    assert (await client.get("/api/report-jobs", headers=headers)).json()["items"] == []


async def test_reviewed_plan_revision_starts_research_and_is_frozen(
    client: AsyncClient, container: Container, user: User
) -> None:
    _, headers = await prepared(container, client)
    plan = await _plan(client, headers)
    brief_id = await _brief(client, headers, plan["id"])
    response = await _start(client, headers, brief_id, plan["updated_at"])
    assert response.status_code == 202, response.text
    job = await stored(container, response.json()["id"])
    scope = _frozen_scope(job.payload)
    assert scope["plan"] == plan["id"]
    assert scope["collection_plan_revision"] == {
        "id": plan["id"],
        "updated_at": plan["updated_at"].replace("Z", "+00:00"),
    }


async def test_missing_changed_disabled_or_foreign_plans_block_submission(
    client: AsyncClient, container: Container, user: User
) -> None:
    _, headers = await prepared(container, client)
    plan = await _plan(client, headers)
    brief_id = await _brief(client, headers, plan["id"])

    unreviewed = await _start(client, headers, brief_id, None)
    assert unreviewed.status_code == 422, unreviewed.text
    assert "Review the collection plan" in unreviewed.json()["error"]["message"]

    edited = await client.put(
        f"/api/direction/plans/{plan['id']}",
        json={**PLAN, "name": "Renamed", "expected_updated_at": plan["updated_at"]},
        headers=headers,
    )
    assert edited.status_code == 200, edited.text
    stale = await _start(client, headers, brief_id, plan["updated_at"])
    assert stale.status_code == 409, stale.text
    assert "changed after you reviewed it" in stale.json()["error"]["message"]

    disabled = await client.put(
        f"/api/direction/plans/{plan['id']}",
        json={**PLAN, "enabled": False, "expected_updated_at": edited.json()["updated_at"]},
        headers=headers,
    )
    refused = await _start(client, headers, brief_id, disabled.json()["updated_at"])
    assert refused.status_code == 422, refused.text
    assert "disabled" in refused.json()["error"]["message"]
    await _no_jobs(client, headers)

    deleted = await client.delete(f"/api/direction/plans/{plan['id']}", headers=headers)
    assert deleted.status_code == 204
    missing = await _start(client, headers, brief_id, disabled.json()["updated_at"])
    assert missing.status_code == 404, missing.text
    await _no_jobs(client, headers)


async def test_another_owners_plan_is_not_disclosed_or_used(
    client: AsyncClient, container: Container, user: User
) -> None:
    _, headers = await prepared(container, client)
    await create_user(container, email="other@example.com", password="another-long-passphrase")
    other = bearer(await login_token(client, "other@example.com", "another-long-passphrase"))
    foreign = await _plan(client, other)
    brief_id = await _brief(client, headers, foreign["id"])
    response = await _start(client, headers, brief_id, foreign["updated_at"])
    assert response.status_code == 404, response.text
    assert "Border watch" not in response.text
    await _no_jobs(client, headers)
