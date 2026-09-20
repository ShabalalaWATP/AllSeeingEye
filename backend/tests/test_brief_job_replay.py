"""Lost brief-run responses replay the admitted observation window, not a new run."""

import asyncio
from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest

from ase.application.report_jobs.service import ReportJobService
from ase.application.reports.generate import GenerateReportUseCase
from ase.domain.teams import MembershipRole
from report_job_api_helpers import prepared, stored
from team_helpers import CONTEXT, team_service
from test_research_brief_api import _draft


@pytest.fixture(name="settings")
def replay_settings(settings, tmp_path):
    if settings.database_url.startswith("postgresql"):
        return settings
    return settings.model_copy(
        update={"database_url": f"sqlite+aiosqlite:///{(tmp_path / 'replay.sqlite').as_posix()}"}
    )


async def brief_body(client, headers, *, team_id=None):
    draft = _draft()
    draft["team_id"] = str(team_id) if team_id else None
    draft["observation"]["policy"] = "relative"
    draft["observation"]["lookback_hours"] = 24
    response = await client.post("/api/research/briefs", json=draft, headers=headers)
    assert response.status_code == 201, response.text
    return draft, {
        "request_id": str(uuid4()),
        "brief_id": response.json()["brief"]["identity"]["id"],
        "revision": 1,
    }


async def test_lost_response_retry_reuses_frozen_window_without_preparing(
    client, container, user, clock
):
    gateway, headers = await prepared(container, client)
    _, body = await brief_body(client, headers)
    first = await client.post("/api/report-jobs/from-brief", json=body, headers=headers)
    assert first.status_code == 202, first.text
    original = await stored(container, first.json()["id"])
    interval = original.payload["input"]
    assert interval["period_from"] and interval["period_to"]
    clock.advance(timedelta(minutes=5))
    with patch.object(
        GenerateReportUseCase, "prepare_job", side_effect=AssertionError("duplicate work")
    ):
        replay = await client.post("/api/report-jobs/from-brief", json=body, headers=headers)
    assert replay.status_code == 202, replay.text
    assert replay.json()["id"] == first.json()["id"]
    assert (await stored(container, original.id)).payload == original.payload
    listed = await client.get("/api/report-jobs", headers=headers)
    assert len(listed.json()["items"]) == 1
    assert gateway.calls == []


@pytest.mark.parametrize("different", ["brief", "revision"])
async def test_reused_request_id_rejects_a_different_immutable_brief(
    client, container, user, different
):
    _, headers = await prepared(container, client)
    draft, body = await brief_body(client, headers)
    first = await client.post("/api/report-jobs/from-brief", json=body, headers=headers)
    assert first.status_code == 202, first.text
    if different == "brief":
        _, other = await brief_body(client, headers)
        retry = {**other, "request_id": body["request_id"]}
    else:
        revised = await client.post(
            f"/api/research/briefs/{body['brief_id']}/revisions",
            json={**draft, "base_revision": 1},
            headers=headers,
        )
        assert revised.status_code == 201, revised.text
        retry = {**body, "revision": 2}
    response = await client.post("/api/report-jobs/from-brief", json=retry, headers=headers)
    assert response.status_code == 409, response.text
    assert first.json()["id"] not in response.text


async def test_replay_does_not_reveal_job_after_team_access_is_removed(
    client, container, user, admin
):
    _, headers = await prepared(container, client)
    async with team_service(container) as service:
        team = await service.create(admin, "Research retry desk", CONTEXT)
        await service.set_member(
            admin, team.id, email=user.email, role=MembershipRole.MEMBER, context=CONTEXT
        )
    _, body = await brief_body(client, headers, team_id=team.id)
    first = await client.post("/api/report-jobs/from-brief", json=body, headers=headers)
    assert first.status_code == 202, first.text
    async with team_service(container) as service:
        await service.remove_member(admin, team.id, user.id, CONTEXT)
    replay = await client.post("/api/report-jobs/from-brief", json=body, headers=headers)
    assert replay.status_code in {401, 404}, replay.text
    assert first.json()["id"] not in replay.text


async def test_concurrent_brief_retries_with_different_resolved_intervals_admit_once(
    client, container, user, clock, monkeypatch
):
    _, headers = await prepared(container, client)
    _, body = await brief_body(client, headers)
    first_prepared, both_prepared = asyncio.Event(), asyncio.Event()
    original = ReportJobService.prepare_candidate
    candidates = []

    async def prepare(service, *args):
        candidate = await original(service, *args)
        candidates.append(candidate)
        if len(candidates) == 1:
            first_prepared.set()
            await both_prepared.wait()
        else:
            both_prepared.set()
        return candidate

    monkeypatch.setattr(ReportJobService, "prepare_candidate", prepare)
    async with asyncio.timeout(30):
        first = asyncio.create_task(
            client.post("/api/report-jobs/from-brief", json=body, headers=headers)
        )
        await first_prepared.wait()
        clock.advance(timedelta(minutes=2))
        second = asyncio.create_task(
            client.post("/api/report-jobs/from-brief", json=body, headers=headers)
        )
        responses = await asyncio.gather(first, second)
    assert [response.status_code for response in responses] == [202, 202]
    assert responses[0].json()["id"] == responses[1].json()["id"]
    assert candidates[0].payload["request_digest"] != candidates[1].payload["request_digest"]
    admitted = await stored(container, responses[0].json()["id"])
    assert admitted.payload in [candidate.payload for candidate in candidates]
    listed = await client.get("/api/report-jobs", headers=headers)
    assert len(listed.json()["items"]) == 1
