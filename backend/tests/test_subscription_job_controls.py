"""Operator job controls cannot strand or erase a subscription edition."""

from datetime import timedelta
from uuid import UUID

from httpx import AsyncClient

from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.container import Container
from ase.domain.subscription_editions import EditionWorkflow
from ase.domain.users import User
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token
from llm_fixture_helpers import seed_legacy_profile
from report_helpers import PROFILE


async def test_pause_resume_and_discard_keep_edition_and_job_in_sync(
    client: AsyncClient, container: Container, user: User
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    await seed_legacy_profile(container, {**PROFILE, "roles": ["assessment"]})
    now = container.clock.now()
    created = await client.post(
        "/api/schedules",
        json={
            "name": "Control test",
            "template_id": "intsum",
            "country_iso": "UA",
            "hour_utc": (now.hour + 1) % 24,
        },
        headers=bearer(token),
    )
    assert created.status_code == 201, created.text
    container.clock.advance(timedelta(hours=2))
    assert await container.schedule_runner.run_once() == 1
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)

    async with container.session_factory() as session:
        edition = await SqlSubscriptionEditionRepository(session).active(UUID(created.json()["id"]))
        assert edition is not None and edition.workflow is EditionWorkflow.QUEUED
        job_id = edition.job_id
    assert job_id is not None
    paused = await client.post(f"/api/report-jobs/{job_id}/pause", headers=bearer(token))
    assert paused.status_code == 200, paused.text
    async with container.session_factory() as session:
        edition = await SqlSubscriptionEditionRepository(session).get(edition.id)
        assert edition is not None and edition.workflow is EditionWorkflow.PAUSED
    discarded = await client.delete(f"/api/report-jobs/{job_id}", headers=bearer(token))
    assert discarded.status_code == 422

    resumed = await client.post(f"/api/report-jobs/{job_id}/resume", headers=bearer(token))
    assert resumed.status_code == 202, resumed.text
    async with container.session_factory() as session:
        edition = await SqlSubscriptionEditionRepository(session).get(edition.id)
        assert edition is not None and edition.workflow is EditionWorkflow.QUEUED
        assert edition.job_id == job_id
    again = await client.post(f"/api/report-jobs/{job_id}/resume", headers=bearer(token))
    assert again.status_code == 202
