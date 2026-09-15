"""A one-off job pins an authorised brief revision and its exact requirements."""

from copy import deepcopy
from datetime import UTC, datetime
from uuid import uuid4

from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token
from report_job_api_helpers import job_settings, prepared, stored, work
from test_research_brief_api import _draft

__all__ = ["job_settings"]


async def test_from_brief_pins_revision_and_all_authored_questions(client, container, user) -> None:
    _, headers = await prepared(container, client)
    draft = _draft()
    draft["question"]["requirements"] = [
        {"id": "IR-1", "question": "What changed?", "required": True, "priority": 1},
        {"id": "IR-2", "question": "What remains uncertain?", "required": True, "priority": 2},
    ]
    created = await client.post("/api/research/briefs", json=draft, headers=headers)
    assert created.status_code == 201, created.text
    brief_id = created.json()["brief"]["identity"]["id"]
    request_id = str(uuid4())
    body = {"request_id": request_id, "brief_id": brief_id, "revision": 1}
    response = await client.post("/api/report-jobs/from-brief", json=body, headers=headers)
    assert response.status_code == 202, response.text
    assert (response.json()["brief_id"], response.json()["brief_revision"]) == (brief_id, 1)
    job = await stored(container, response.json()["id"])
    assert (str(job.brief_id), job.brief_revision) == (brief_id, 1)
    assert [row["id"] for row in job.payload["input"]["request"]["canonical_requirements"]] == [
        "IR-1",
        "IR-2",
    ]
    repeated = await client.post("/api/report-jobs/from-brief", json=body, headers=headers)
    assert repeated.status_code == 202
    assert repeated.json()["id"] == response.json()["id"]
    await work(container)
    completed = await stored(container, job.id)
    assert completed.status in {"completed", "needs_review"}, (
        completed.status,
        completed.error,
        completed.stage,
    )
    async with container.session_factory() as session:
        saved = await container.repositories(session).reports.get_version(job.report_id, 1)
    assert saved is not None
    assert (str(saved.brief_id), saved.brief_revision) == (brief_id, 1)
    assert [row.question for row in saved.canonical_requirements] == [
        "What changed?",
        "What remains uncertain?",
    ]


async def test_from_brief_rejects_unsupported_choices_before_admission(
    client, container, user
) -> None:
    _, headers = await prepared(container, client)
    draft = _draft()
    draft["lens"]["audience"] = "Private research sentinel"
    created = await client.post("/api/research/briefs", json=draft, headers=headers)
    assert created.status_code == 201, created.text
    brief_id = created.json()["brief"]["identity"]["id"]
    body = {"request_id": str(uuid4()), "brief_id": brief_id, "revision": 1}
    response = await client.post("/api/report-jobs/from-brief", json=body, headers=headers)
    assert response.status_code == 422
    assert "Private research sentinel" not in response.text
    assert (await client.get("/api/report-jobs", headers=headers)).json()["items"] == []


async def test_from_brief_requires_current_object_access(client, container, user) -> None:
    draft = deepcopy(_draft())
    owner_token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    owner_headers = bearer(owner_token)
    created = await client.post("/api/research/briefs", json=draft, headers=owner_headers)
    assert created.status_code == 201, created.text
    brief_id = created.json()["brief"]["identity"]["id"]
    response = await client.post(
        "/api/report-jobs/from-brief",
        json={"request_id": str(uuid4()), "brief_id": brief_id, "revision": 2},
        headers=owner_headers,
    )
    assert response.status_code == 404


async def test_explicit_observation_can_be_saved_without_codec_loss(
    client, container, user
) -> None:
    _, headers = await prepared(container, client)
    draft = _draft()
    draft["observation"] = {
        "policy": "explicit",
        "since": "2026-08-01T00:00:00+00:00",
        "until": "2026-08-31T00:00:00+00:00",
        "lookback_hours": None,
        "time_basis": None,
        "forecast_horizon_days": None,
    }
    response = await client.post("/api/research/briefs", json=draft, headers=headers)
    assert response.status_code == 201, response.text
    saved = response.json()["brief"]["observation"]
    assert datetime.fromisoformat(saved["since"]) == datetime(2026, 8, 1, tzinfo=UTC)
    assert datetime.fromisoformat(saved["until"]) == datetime(2026, 8, 31, tzinfo=UTC)
