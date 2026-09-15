"""Subscription operational metrics are truthful, bounded and administrator-only."""

from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.application.schedules.manage import ScheduleInput
from ase.application.schedules.revision_snapshot import revision_from_schedule
from ase.domain.subscription_editions import (
    EditionCoverage,
    EditionQuality,
    EditionTrigger,
    EditionWorkflow,
    ObservationInterval,
    SubscriptionEdition,
)
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, USER_EMAIL, USER_PASSWORD, bearer, login_token
from llm_fixture_helpers import seed_legacy_profile
from report_helpers import PROFILE
from team_helpers import CONTEXT


async def _blocked_edition(container, user, reason: str) -> None:
    async with container.session_factory() as session:
        schedule = await container.create_schedule(session).execute(
            user,
            ScheduleInput(name="Private diagnostic question", template_id="intsum"),
            CONTEXT,
        )
    async with container.session_factory() as session:
        ledger = SqlSubscriptionEditionRepository(session)
        revision = revision_from_schedule(schedule, 1)
        await ledger.add_revision(revision)
        requested = ObservationInterval(
            schedule.next_run_at - timedelta(days=1), schedule.next_run_at
        )
        pending = await ledger.reserve(
            SubscriptionEdition(
                id=uuid4(),
                subscription_id=schedule.id,
                trigger=EditionTrigger.SCHEDULED,
                due_at_utc=schedule.next_run_at,
                request_uuid=None,
                frozen_revision=1,
                requested=requested,
                effective_intervals=(),
                gaps=(requested,),
                compatibility_fingerprint=revision.compatibility_fingerprint,
                baseline_version_id=None,
                workflow=EditionWorkflow.PENDING,
                report_quality=EditionQuality.ABSENT,
                coverage=EditionCoverage.UNKNOWN,
                created_at=container.clock.now(),
                updated_at=container.clock.now(),
            )
        )
        await ledger.advance(
            replace(
                pending,
                workflow=EditionWorkflow.BLOCKED,
                safe_reason=reason,
                revision=pending.revision + 1,
            ),
            expected_revision=pending.revision,
        )
        await session.commit()


async def test_admin_diagnostics_show_due_lag_and_admission_without_user_data(
    client, container, admin, user
) -> None:
    endpoint = "/api/admin/subscriptions/diagnostics"
    assert (await client.get(endpoint)).status_code == 401
    user_token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    assert (await client.get(endpoint, headers=bearer(user_token))).status_code == 403
    admin_token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    headers = bearer(admin_token)
    empty = await client.get(endpoint, headers=headers)
    assert empty.status_code == 200, empty.text
    assert empty.headers["cache-control"] == "private, no-store"
    assert empty.json()["enabled_subscriptions"] == 0
    assert empty.json()["oldest_due_lag_seconds"] is None

    await seed_legacy_profile(container, {**PROFILE, "roles": ["assessment"]})
    now = container.clock.now()
    created = await client.post(
        "/api/schedules",
        json={
            "name": "Private queue health fixture",
            "template_id": "intsum",
            "country_iso": "UA",
            "hour_utc": (now.hour + 1) % 24,
        },
        headers=bearer(user_token),
    )
    assert created.status_code == 201, created.text
    container.clock.advance(timedelta(hours=2))
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    overdue = await client.get(endpoint, headers=headers)
    assert overdue.status_code == 200, overdue.text
    assert overdue.json()["enabled_subscriptions"] == 1
    assert overdue.json()["overdue_subscriptions"] == 1
    assert overdue.json()["oldest_due_lag_seconds"] > 0
    assert "Private queue health fixture" not in overdue.text

    assert await container.schedule_runner.run_once() == 1
    admitted = await client.get(endpoint, headers=headers)
    assert admitted.status_code == 200, admitted.text
    body = admitted.json()
    assert body["overdue_subscriptions"] == 0
    assert body["active_editions_by_workflow"]["queued"] == 1
    assert body["last_admitted_job_at"] is not None
    assert body["open_report_jobs"] == 1
    assert body["global_open_job_limit"] > body["open_report_jobs"]
    assert body["queue_saturated"] is False


async def test_admin_diagnostics_count_only_allowlisted_source_failure_codes(
    client, container, admin, user
) -> None:
    for reason in (
        "source_failure_coverage",
        "source_failure_coverage",
        "source_disabled",
        "private_question_marker",
    ):
        await _blocked_edition(container, user, reason)
    admin_headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    response = await client.get("/api/admin/subscriptions/diagnostics", headers=admin_headers)
    assert response.status_code == 200, response.text
    assert response.json()["source_failure_categories"] == {
        "source_failure_coverage": 2,
        "source_disabled": 1,
    }
    assert response.json()["source_failure_editions"] == 3
    assert "Private diagnostic question" not in response.text
    assert "private_question_marker" not in response.text
