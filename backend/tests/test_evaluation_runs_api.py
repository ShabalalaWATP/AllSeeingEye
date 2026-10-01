"""HTTP contract for administrator evaluation runs: MFA admins only, no secrets released."""

from __future__ import annotations

import asyncio
from uuid import uuid4

from ase.application.dto import RequestContext
from ase.domain.audit import AuditAction
from evaluation_run_helpers import (
    CORE_CASES,
    ScriptedRunGateway,
    assert_no_secrets,
    evaluation_profile,
    unzipped,
)
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, USER_EMAIL, USER_PASSWORD, bearer, login_token

BASE = "/api/admin/llm/evaluations"


async def _admin_headers(client) -> dict[str, str]:
    return bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))


async def test_administrators_see_the_catalogue_and_estimate(client, admin) -> None:
    headers = await _admin_headers(client)
    response = await client.get(f"{BASE}/catalogue", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["cases"]) == 20
    assert {case["casebook"] for case in body["cases"]} == {"core", "regional"}
    assert body["calls_per_case"] == 4 and body["max_calls"] == 200
    assert "Estimate" in body["estimate_notice"]
    assert "accuracy" in body["result_notice"]


async def test_a_run_starts_completes_and_offers_a_secret_free_download(
    client, container, admin
) -> None:
    headers = await _admin_headers(client)
    profile = await evaluation_profile(container)
    container.llm = ScriptedRunGateway()
    started = await client.post(
        BASE,
        headers=headers,
        json={"profile_id": str(profile.id), "case_ids": CORE_CASES[:1], "max_calls": 6},
    )
    assert started.status_code == 202, started.text
    run = started.json()
    assert run["status"] == "running" and run["estimated_calls"] == 4
    assert run["max_calls"] == 6 and run["case_ids"] == CORE_CASES[:1]
    await container.evaluation_tasks.drain()
    detail = await client.get(f"{BASE}/{run['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["status"] == "completed" and detail.json()["has_artefact"]
    listing = await client.get(BASE, headers=headers)
    assert [item["id"] for item in listing.json()["items"]] == [run["id"]]
    download = await client.get(f"{BASE}/{run['id']}/artefact", headers=headers)
    assert download.status_code == 200
    assert download.headers["content-type"] == "application/zip"
    assert "attachment" in download.headers["content-disposition"]
    assert_no_secrets(
        started.content, detail.content, listing.content, download.content,
        *unzipped(download.content).values(),
    )  # fmt: skip
    # Cancelling a finished run changes nothing.
    cancelled = await client.post(f"{BASE}/{run['id']}/cancel", headers=headers)
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "completed"


async def test_a_second_start_conflicts_and_the_first_can_be_cancelled(
    client, container, admin
) -> None:
    headers = await _admin_headers(client)
    profile = await evaluation_profile(container)
    release = asyncio.Event()

    async def wait(count: int) -> None:
        await release.wait()

    container.llm = ScriptedRunGateway(hook=wait)
    body = {"profile_id": str(profile.id), "case_ids": CORE_CASES, "max_calls": 8}
    first = await client.post(BASE, headers=headers, json=body)
    assert first.status_code == 202
    await asyncio.sleep(0)
    second = await client.post(BASE, headers=headers, json=body)
    assert second.status_code == 409
    cancelled = await client.post(f"{BASE}/{first.json()['id']}/cancel", headers=headers)
    assert cancelled.status_code == 200 and cancelled.json()["cancel_requested"]
    release.set()
    await container.evaluation_tasks.drain()
    final = await client.get(f"{BASE}/{first.json()['id']}", headers=headers)
    assert final.json()["status"] == "cancelled"
    async with container.session_factory() as session:
        entries = await container.repositories(session).audit.list_before(None, 50)
    audited = {entry.action: entry for entry in entries}
    run_id = first.json()["id"]
    started = audited[AuditAction.EVALUATION_RUN_STARTED]
    assert started.subject == run_id and started.actor_user_id == admin.id
    assert started.details == {
        "profile_id": str(profile.id),
        "cases": len(CORE_CASES),
        "max_calls": 8,
    }
    assert audited[AuditAction.EVALUATION_RUN_CANCELLED].subject == run_id
    # A refused second start records nothing.
    assert sum(entry.action is AuditAction.EVALUATION_RUN_STARTED for entry in entries) == 1


async def test_invalid_requests_are_refused(client, container, admin) -> None:
    headers = await _admin_headers(client)
    profile = await evaluation_profile(container)
    for body in (
        {"profile_id": str(profile.id), "case_ids": ["unknown"], "max_calls": 4},
        {"profile_id": str(profile.id), "case_ids": CORE_CASES, "max_calls": 201},
        {"profile_id": str(profile.id), "case_ids": [], "max_calls": 4},
    ):
        response = await client.post(BASE, headers=headers, json=body)
        assert response.status_code in {400, 422}, body
    missing = await client.get(f"{BASE}/{uuid4()}", headers=headers)
    assert missing.status_code == 404
    no_download = await client.get(f"{BASE}/{uuid4()}/artefact", headers=headers)
    assert no_download.status_code == 404


async def test_non_administrators_are_forbidden(client, admin, user) -> None:
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    run_id = uuid4()
    requests = (
        ("GET", f"{BASE}/catalogue"),
        ("GET", BASE),
        ("POST", BASE),
        ("GET", f"{BASE}/{run_id}"),
        ("POST", f"{BASE}/{run_id}/cancel"),
        ("GET", f"{BASE}/{run_id}/artefact"),
    )
    body = {"profile_id": str(uuid4()), "case_ids": CORE_CASES, "max_calls": 4}
    for method, path in requests:
        response = await client.request(
            method, path, headers=headers, json=body if method == "POST" else None
        )
        assert response.status_code == 403, (method, path)


async def test_administrator_sessions_without_mfa_are_refused(client, container, admin) -> None:
    async with container.session_factory() as session:
        repos = container.repositories(session)
        started = await container._sessions(repos).start(
            admin, RequestContext(ip="test", user_agent="evaluation-test"), mfa_verified=False
        )
        await repos.uow.commit()
    headers = bearer(started.access.token)
    assert (await client.get(f"{BASE}/catalogue", headers=headers)).status_code == 401
    body = {"profile_id": str(uuid4()), "case_ids": CORE_CASES, "max_calls": 4}
    assert (await client.post(BASE, headers=headers, json=body)).status_code == 401
