"""Real HTTP identity, team scope and current-session checks for durable report jobs."""

from datetime import timedelta
from uuid import uuid4

import ase.api.routers.report_jobs as router_module
import ase.application.report_jobs.controls as controls_module
from ase.application.reports.generate import GenerateReportUseCase
from helpers import CSRF_COOKIE, USER_PASSWORD, bearer, create_user, login_token
from report_job_api_helpers import job_settings, prepared, stored, submit, work
from team_helpers import CONTEXT, team_service
from test_report_team_scope import team_for

__all__ = ["job_settings"]


async def test_another_user_cannot_read_list_pause_or_resume_personal_job(client, user, container):
    gateway, headers = await prepared(container, client)
    job_id = (await submit(client, headers)).json()["id"]
    other = await create_user(container, email="other@example.com", password=USER_PASSWORD)
    other_headers = bearer(await login_token(client, other.email, USER_PASSWORD))
    assert (await client.get("/api/report-jobs", headers=other_headers)).json()["items"] == []
    for suffix, method in (("", client.get), ("/pause", client.post), ("/resume", client.post)):
        response = await method(f"/api/report-jobs/{job_id}{suffix}", headers=other_headers)
        assert response.status_code == 404, response.text
    assert (await stored(container, job_id)).status == "queued" and not gateway.calls


async def test_team_scope_is_checked_at_admission_and_again_before_background_work(
    client, user, admin, container
):
    team = await team_for(container, admin, user)
    gateway, headers = await prepared(container, client)
    job_id = (
        await submit(client, headers, report={"template": "intsum", "team_id": str(team.id)})
    ).json()["id"]
    outsider = await create_user(container, email="outside@example.com", password=USER_PASSWORD)
    outsider_headers = bearer(await login_token(client, outsider.email, USER_PASSWORD))
    response = await client.post(
        "/api/report-jobs",
        headers=outsider_headers,
        json={
            "request_id": str(uuid4()),
            "report": {"template": "intsum", "team_id": str(team.id)},
        },
    )
    assert response.status_code == 404
    assert (
        await client.get(f"/api/report-jobs/{job_id}", headers=outsider_headers)
    ).status_code == 404
    async with team_service(container) as service:
        await service.remove_member(admin, team.id, user.id, CONTEXT)
    await work(container)
    current = await stored(container, job_id)
    assert current.status == "paused" and current.error == "access_changed"
    assert not gateway.calls
    assert (await client.get(f"/api/report-jobs/{job_id}", headers=headers)).status_code == 404
    async with container.session_factory() as session:
        assert await container.repositories(session).reports.get(current.report_id) is None


async def test_session_revoked_during_preparation_cannot_admit_a_job(
    client, user, container, monkeypatch
):
    gateway, headers = await prepared(container, client)
    original = GenerateReportUseCase.prepare_job

    async def revoke_after_preparation(self, *args, **kwargs):
        result = await original(self, *args, **kwargs)
        logout = await client.post(
            "/api/auth/logout", headers={"X-CSRF-Token": client.cookies[CSRF_COOKIE]}
        )
        assert logout.status_code == 204
        return result

    monkeypatch.setattr(GenerateReportUseCase, "prepare_job", revoke_after_preparation)
    response = await client.post(
        "/api/report-jobs",
        headers=headers,
        json={"request_id": str(uuid4()), "report": {"template": "intsum"}},
    )
    assert response.status_code == 401, response.text
    assert not gateway.calls
    new_headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    assert (await client.get("/api/report-jobs", headers=new_headers)).json()["items"] == []


async def test_expiry_after_public_projection_prevents_job_response(
    client, user, container, monkeypatch
):
    _, headers = await prepared(container, client)
    job_id = (await submit(client, headers)).json()["id"]
    original = router_module.public_job

    def expire_after_projection(value):
        result = original(value)
        container.clock.advance(timedelta(hours=1))
        return result

    monkeypatch.setattr(router_module, "public_job", expire_after_projection)
    response = await client.get(f"/api/report-jobs/{job_id}", headers=headers)
    assert response.status_code == 401 and "sections" not in response.text


async def test_duplicate_request_id_with_changed_content_is_conflict(client, user, container):
    gateway, headers = await prepared(container, client)
    request_id = uuid4()
    first = (await submit(client, headers, request_id=request_id)).json()
    response = await client.post(
        "/api/report-jobs",
        headers=headers,
        json={
            "request_id": str(request_id),
            "report": {"template": "intsum", "country": "GB"},
        },
    )
    assert response.status_code == 409, response.text
    jobs = (await client.get("/api/report-jobs", headers=headers)).json()["items"]
    assert [job["id"] for job in jobs] == [first["id"]] and not gateway.calls


async def test_discard_requires_pause_and_releases_retained_job_quota(
    client, user, container, monkeypatch
):
    gateway, headers = await prepared(container, client)
    monkeypatch.setattr(controls_module, "MAX_OPEN_PER_OWNER", 1)
    job_id = (await submit(client, headers)).json()["id"]
    assert (await client.delete(f"/api/report-jobs/{job_id}", headers=headers)).status_code == 422
    paused = await client.post(f"/api/report-jobs/{job_id}/pause", headers=headers)
    assert paused.status_code == 200
    blocked = await client.post(
        "/api/report-jobs",
        headers=headers,
        json={"request_id": str(uuid4()), "report": {"template": "intsum"}},
    )
    assert blocked.status_code == 422
    response = await client.delete(f"/api/report-jobs/{job_id}", headers=headers)
    assert response.status_code == 204 and not response.content
    assert await stored(container, job_id) is None
    assert (await client.get(f"/api/report-jobs/{job_id}", headers=headers)).status_code == 404
    assert (await submit(client, headers)).json()["id"] != job_id
    assert not gateway.calls
