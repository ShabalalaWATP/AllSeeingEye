"""Schedule edition controls retain one job and enforce current schedule scope."""

from datetime import timedelta
from uuid import UUID, uuid4

from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.domain.subscription_editions import EditionWorkflow
from helpers import USER_EMAIL, USER_PASSWORD, bearer, create_user, login_token
from llm_fixture_helpers import seed_legacy_profile
from report_helpers import PROFILE
from report_job_api_helpers import work


async def test_edition_pause_resume_retry_are_scoped_and_idempotent(
    client, container, user
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    headers = bearer(token)
    await seed_legacy_profile(container, {**PROFILE, "roles": ["assessment"]})
    now = container.clock.now()
    created = await client.post(
        "/api/schedules",
        json={
            "name": "Controlled edition",
            "template_id": "intsum",
            "country_iso": "UA",
            # Daily explicitly: this test drives the runner, not the creation default.
            "cadence": "daily",
            "hour_utc": (now.hour + 1) % 24,
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    schedule_id = UUID(created.json()["id"])
    container.clock.advance(timedelta(hours=2))
    assert await container.schedule_runner.run_once() == 1
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    async with container.session_factory() as session:
        edition = await SqlSubscriptionEditionRepository(session).active(schedule_id)
    assert edition is not None and edition.workflow is EditionWorkflow.QUEUED
    assert edition.job_id is not None
    path = f"/api/schedules/{schedule_id}/editions/{edition.id}"

    other = await create_user(
        container, email="control-outsider@example.com", password="another-long-passphrase"
    )
    outsider = bearer(await login_token(client, other.email, "another-long-passphrase"))
    assert (await client.post(f"{path}/pause", headers=outsider)).status_code == 404
    wrong_schedule = f"/api/schedules/{uuid4()}/editions/{edition.id}/pause"
    assert (await client.post(wrong_schedule, headers=headers)).status_code == 404

    paused = await client.post(f"{path}/pause", headers=headers)
    assert paused.status_code == 200, paused.text
    assert paused.json()["workflow"] == "paused"
    assert paused.json()["job_id"] == str(edition.job_id)
    again = await client.post(f"{path}/pause", headers=headers)
    assert again.status_code == 200 and again.json()["id"] == paused.json()["id"]

    retried = await client.post(f"{path}/retry", headers=headers)
    assert retried.status_code == 202, retried.text
    assert retried.json()["workflow"] == "queued"
    assert retried.json()["job_id"] == str(edition.job_id)
    repeated = await client.post(f"{path}/retry", headers=headers)
    assert repeated.status_code == 202 and repeated.json()["id"] == retried.json()["id"]

    assert (await client.post(f"{path}/pause", headers=headers)).status_code == 200
    resumed = await client.post(f"{path}/resume", headers=headers)
    assert resumed.status_code == 202 and resumed.json()["workflow"] == "queued"
    assert (await client.post(f"{path}/resume", headers=headers)).status_code == 202

    await work(container)
    current = await client.get(f"/api/schedules/{schedule_id}/editions", headers=headers)
    assert current.json()["items"][0]["workflow"] == "completed"
    assert (await client.post(f"{path}/retry", headers=headers)).status_code == 409
