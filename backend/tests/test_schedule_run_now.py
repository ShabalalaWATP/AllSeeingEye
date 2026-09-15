"""Manual subscription runs keep cadence and admit one job per request UUID."""

from datetime import timedelta
from unittest.mock import patch
from uuid import UUID, uuid4

from sqlalchemy import select

from ase.adapters.persistence.models import AuditLogRow
from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.application.auditing import Auditor
from helpers import USER_EMAIL, USER_PASSWORD, bearer, create_user, login_token
from llm_fixture_helpers import seed_legacy_profile
from report_helpers import PROFILE


async def test_run_now_is_scoped_idempotent_and_does_not_move_cadence(
    client, container, user
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    headers = bearer(token)
    await seed_legacy_profile(container, {**PROFILE, "roles": ["assessment"]})
    created = await client.post(
        "/api/schedules",
        json={"name": "Manual updates", "template_id": "intsum", "country_iso": "UA"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    schedule = created.json()
    endpoint = f"/api/schedules/{schedule['id']}/run-now"
    request_id = str(uuid4())

    other = await create_user(
        container, email="manual-outsider@example.com", password="another-long-passphrase"
    )
    outsider = bearer(await login_token(client, other.email, "another-long-passphrase"))
    assert (
        await client.post(endpoint, json={"request_id": request_id}, headers=outsider)
    ).status_code == 404

    first = await client.post(endpoint, json={"request_id": request_id}, headers=headers)
    assert first.status_code == 202, first.text
    edition = first.json()
    assert edition["trigger"] == "run_now"
    assert edition["due_at_utc"] is None
    assert edition["job_id"] is not None
    repeated = await client.post(endpoint, json={"request_id": request_id}, headers=headers)
    assert repeated.status_code == 202 and repeated.json()["id"] == edition["id"]
    conflict = await client.post(endpoint, json={"request_id": str(uuid4())}, headers=headers)
    assert conflict.status_code == 409
    current = await client.get("/api/schedules", headers=headers)
    assert current.json()["items"][0]["next_run_at"] == schedule["next_run_at"]
    async with container.session_factory() as session:
        editions = await SqlSubscriptionEditionRepository(session).history(UUID(schedule["id"]))
        audits = list(
            await session.scalars(select(AuditLogRow).where(AuditLogRow.subject == schedule["id"]))
        )
    assert len(editions) == 1
    assert len([row for row in audits if row.details.get("action") == "run_now"]) == 1


async def test_run_now_rolls_back_if_original_session_expires_during_admission(
    client, container, user
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    headers = bearer(token)
    await seed_legacy_profile(container, {**PROFILE, "roles": ["assessment"]})
    created = await client.post(
        "/api/schedules",
        json={"name": "Manual fence", "template_id": "intsum", "country_iso": "UA"},
        headers=headers,
    )
    assert created.status_code == 201
    schedule_id = UUID(created.json()["id"])
    original = Auditor.record

    async def delayed(self, action, **kwargs):
        result = await original(self, action, **kwargs)
        if kwargs.get("details", {}).get("action") == "run_now":
            container.clock.advance(timedelta(days=1))
        return result

    with patch.object(Auditor, "record", delayed):
        response = await client.post(
            f"/api/schedules/{schedule_id}/run-now",
            json={"request_id": str(uuid4())},
            headers=headers,
        )
    assert response.status_code == 401
    async with container.session_factory() as session:
        assert await SqlSubscriptionEditionRepository(session).history(schedule_id) == []
