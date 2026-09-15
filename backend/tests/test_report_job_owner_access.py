"""Reads and pauses authorise the caller; only work-starting controls need the owner."""

from sqlalchemy import update

from ase.adapters.persistence.models import UserRow
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, bearer, login_token
from report_job_api_helpers import job_settings, prepared, stored, submit
from team_helpers import CONTEXT, team_service
from test_report_team_scope import team_for

__all__ = ["job_settings"]


async def _deactivate(container, user_id):
    async with container.session_factory() as session:
        await session.execute(update(UserRow).where(UserRow.id == user_id).values(is_active=False))
        await session.commit()


async def _admin_headers(client):
    return bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))


async def test_admin_reads_paused_job_after_owner_deactivation(client, user, admin, container):
    gateway, headers = await prepared(container, client)
    job_id = (await submit(client, headers)).json()["id"]
    paused = await client.post(f"/api/report-jobs/{job_id}/pause", headers=headers)
    assert paused.status_code == 200, paused.text
    admin_headers = await _admin_headers(client)
    await _deactivate(container, user.id)
    response = await client.get(f"/api/report-jobs/{job_id}", headers=admin_headers)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "paused"
    listed = (await client.get("/api/report-jobs", headers=admin_headers)).json()["items"]
    assert [item["id"] for item in listed] == [job_id]
    # Resume starts work, so the inactive owner refuses it without ending the admin session.
    resumed = await client.post(f"/api/report-jobs/{job_id}/resume", headers=admin_headers)
    assert resumed.status_code == 403, resumed.text
    assert (await stored(container, job_id)).status == "paused"
    assert (await client.get("/api/me", headers=admin_headers)).status_code == 200
    assert not gateway.calls


async def test_admin_pauses_queued_job_of_deactivated_owner(client, user, admin, container):
    gateway, headers = await prepared(container, client)
    job_id = (await submit(client, headers)).json()["id"]
    admin_headers = await _admin_headers(client)
    await _deactivate(container, user.id)
    response = await client.post(f"/api/report-jobs/{job_id}/pause", headers=admin_headers)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "paused"
    assert (await stored(container, job_id)).status == "paused"
    assert not gateway.calls


async def test_archived_team_job_stays_readable_but_cannot_resume(client, user, admin, container):
    team = await team_for(container, admin, user)
    gateway, headers = await prepared(container, client)
    job_id = (
        await submit(client, headers, report={"template": "intsum", "team_id": str(team.id)})
    ).json()["id"]
    assert (await client.post(f"/api/report-jobs/{job_id}/pause", headers=headers)).is_success
    async with team_service(container) as service:
        await service.update(admin, team.id, name=None, is_active=False, context=CONTEXT)
    admin_headers = await _admin_headers(client)
    for caller in (headers, admin_headers):
        response = await client.get(f"/api/report-jobs/{job_id}", headers=caller)
        assert response.status_code == 200, response.text
        resumed = await client.post(f"/api/report-jobs/{job_id}/resume", headers=caller)
        assert resumed.status_code in {403, 422}, resumed.text
    assert (await stored(container, job_id)).status == "paused"
    assert not gateway.calls
