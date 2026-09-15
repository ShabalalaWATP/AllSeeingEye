"""Persist local recurrence settings and use original due slots after an outage."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

from httpx import AsyncClient

from ase.adapters.persistence.operational_models import ReportRow, ReportVersionRow
from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.application.schedules.manage import ScheduleInput
from ase.application.schedules.revision_snapshot import revision_from_schedule
from ase.container import Container
from ase.domain.errors import RateLimited
from ase.domain.subscription_editions import (
    EditionCoverage,
    EditionQuality,
    EditionTrigger,
    EditionWorkflow,
    ObservationInterval,
    SubscriptionEdition,
    SubscriptionLineage,
    scheduled_edition_id,
)
from ase.domain.subscription_monthly_budget import MonthlyBudgetExhausted
from ase.domain.subscription_recurrence import WindowPolicy
from ase.domain.users import User
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token
from llm_fixture_helpers import seed_legacy_profile
from report_helpers import PROFILE
from team_helpers import CONTEXT


async def _local_schedule(container: Container, user: User, **changes: object):
    await seed_legacy_profile(container, {**PROFILE, "roles": ["assessment"]})
    data = {
        "name": "Local subscription",
        "template_id": "intsum",
        "country_iso": "UA",
        "timezone": "Europe/London",
        "local_hour": 1,
        "local_minute": 30,
        "cadence": "daily",
        "window_hours": 48,
    }
    data.update(changes)
    async with container.session_factory() as session:
        return await container.create_schedule(session).execute(
            user, ScheduleInput(**data), CONTEXT
        )


async def test_local_schedule_persists_and_previews_dst_gap(
    container: Container, user: User
) -> None:
    container.clock.advance(datetime(2027, 3, 27, 12, tzinfo=UTC) - container.clock.now())
    schedule = await _local_schedule(container, user)
    assert schedule.next_run_at == datetime(2027, 3, 28, 1, tzinfo=UTC)
    async with container.session_factory() as session:
        stored = await container.repositories(session).schedules.get(schedule.id)
    assert stored is not None
    assert (stored.timezone, stored.local_hour, stored.local_minute) == ("Europe/London", 1, 30)
    assert [item.utc for item in stored.next_three] == [
        datetime(2027, 3, 28, 1, tzinfo=UTC),
        datetime(2027, 3, 29, 0, 30, tzinfo=UTC),
        datetime(2027, 3, 30, 0, 30, tzinfo=UTC),
    ]


async def test_repeated_local_hour_uses_earlier_instant_once(
    container: Container, user: User
) -> None:
    container.clock.advance(datetime(2027, 10, 30, 12, tzinfo=UTC) - container.clock.now())
    schedule = await _local_schedule(container, user)
    assert schedule.next_run_at == datetime(2027, 10, 31, 0, 30, tzinfo=UTC)
    assert schedule.next_three[0].dst_resolution == "fold"
    assert schedule.next_three[1].utc == datetime(2027, 11, 1, 1, 30, tzinfo=UTC)


async def test_schedule_api_exposes_local_preview_and_rejects_unknown_zone(
    client: AsyncClient, container: Container, user: User
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    body = {
        "name": "London briefing",
        "template_id": "intsum",
        "country_iso": "UA",
        "timezone": "Europe/London",
        "local_hour": 6,
        "local_minute": 15,
        "collection_policy": "since_last_success",
    }
    bad = await client.post(
        "/api/schedules", json={**body, "timezone": "Mars/Olympus"}, headers=bearer(token)
    )
    assert bad.status_code == 422
    created = await client.post("/api/schedules", json=body, headers=bearer(token))
    assert created.status_code == 201, created.text
    item = created.json()
    assert (item["timezone"], item["local_hour"], item["local_minute"]) == ("Europe/London", 6, 15)
    assert item["collection_policy"] == "since_last_success"
    assert len(item["next_three"]) == 3
    assert item["next_three"][0]["utc"] == item["next_run_at"]


async def test_five_day_outage_creates_one_catch_up_job_with_skipped_links(
    container: Container, user: User
) -> None:
    schedule = await _local_schedule(container, user, timezone="UTC", local_hour=6)
    first = schedule.next_run_at
    container.clock.advance(first - container.clock.now() + timedelta(days=5, minutes=1))
    assert await container.schedule_runner.run_once() == 1
    async with container.session_factory() as session:
        ledger = SqlSubscriptionEditionRepository(session)
        editions = await ledger.history(schedule.id)
        current = await container.repositories(session).schedules.get(schedule.id)
    assert current is not None
    assert len(editions) == 6
    queued = [item for item in editions if item.workflow is EditionWorkflow.QUEUED]
    skipped = [item for item in editions if item.workflow is EditionWorkflow.SKIPPED]
    assert len(queued) == 1 and len(skipped) == 5
    assert queued[0].trigger is EditionTrigger.CATCH_UP
    assert queued[0].due_at_utc == first + timedelta(days=5)
    assert queued[0].requested.end == queued[0].due_at_utc
    assert queued[0].requested.start == queued[0].due_at_utc - timedelta(hours=48)
    assert all(item.covered_by_edition_id == queued[0].id for item in skipped)
    assert current.next_run_at == first + timedelta(days=6)
    assert queued[0].job_id is not None
    async with container.session_factory() as session:
        job = await SqlReportJobRepository(session).get(queued[0].job_id)
    assert job is not None
    frozen = job.payload["input"]
    assert frozen["period_from"] == queued[0].requested.start.isoformat()
    assert frozen["period_to"] == queued[0].requested.end.isoformat()
    assert frozen["scope"]["research_since"] == queued[0].requested.start.isoformat()
    assert frozen["scope"]["research_until"] == queued[0].requested.end.isoformat()
    assert await container.schedule_runner.run_once() == 0


async def test_capacity_pending_is_coalesced_only_before_paid_admission(
    container: Container, user: User
) -> None:
    schedule = await _local_schedule(container, user, timezone="UTC", local_hour=6)
    first = schedule.next_run_at
    container.clock.advance(first - container.clock.now() + timedelta(minutes=1))
    with patch("ase.application.report_jobs.service.require_capacity", side_effect=RateLimited(60)):
        assert await container.schedule_runner.run_once() == 0
    container.clock.advance(timedelta(days=5))
    assert await container.schedule_runner.run_once() == 1
    async with container.session_factory() as session:
        editions = await SqlSubscriptionEditionRepository(session).history(schedule.id)
    old = next(item for item in editions if item.due_at_utc == first)
    latest = next(item for item in editions if item.workflow is EditionWorkflow.QUEUED)
    assert old.workflow is EditionWorkflow.SKIPPED
    assert old.covered_by_edition_id == latest.id
    assert latest.due_at_utc == first + timedelta(days=5)


async def test_scope_edit_preserves_frozen_pending_work_during_outage(
    container: Container, user: User
) -> None:
    schedule = await _local_schedule(container, user, timezone="UTC", local_hour=6)
    first = schedule.next_run_at
    container.clock.advance(first - container.clock.now() + timedelta(minutes=1))
    with patch("ase.application.report_jobs.service.require_capacity", side_effect=RateLimited(60)):
        assert await container.schedule_runner.run_once() == 0
    async with container.session_factory() as session:
        edited = await container.update_schedule(session).execute(
            user,
            schedule.id,
            ScheduleInput(
                name="Changed scope",
                template_id="intsum",
                country_iso="UA",
                question="What changed in the selected period?",
                timezone="UTC",
                local_hour=6,
            ),
            CONTEXT,
        )
    container.clock.advance(timedelta(days=5))
    assert await container.schedule_runner.run_once() == 1
    async with container.session_factory() as session:
        editions = await SqlSubscriptionEditionRepository(session).history(schedule.id)
        current = await container.repositories(session).schedules.get(schedule.id)
    assert len(editions) == 1 and editions[0].workflow is EditionWorkflow.QUEUED
    assert editions[0].due_at_utc == first
    assert current is not None and current.next_run_at == edited.next_run_at


async def test_monthly_budget_block_does_not_advance_due_slot_or_create_job(
    container: Container, user: User
) -> None:
    schedule = await _local_schedule(container, user, timezone="UTC", local_hour=6)
    container.clock.advance(schedule.next_run_at - container.clock.now() + timedelta(minutes=1))
    with patch(
        "ase.application.report_jobs.service.ReportJobService.admit_prepared",
        side_effect=MonthlyBudgetExhausted(),
    ):
        assert await container.schedule_runner.run_once() == 0
    async with container.session_factory() as session:
        edition = await SqlSubscriptionEditionRepository(session).active(schedule.id)
        current = await container.repositories(session).schedules.get(schedule.id)
    assert edition is not None and edition.workflow is EditionWorkflow.BLOCKED
    assert edition.job_id is None and edition.safe_reason == "monthly_budget_exhausted"
    assert current is not None and current.next_run_at == schedule.next_run_at


async def test_since_last_success_uses_compatible_cutoff_with_bounded_overlap(
    container: Container, user: User
) -> None:
    schedule = await _local_schedule(
        container,
        user,
        timezone="UTC",
        local_hour=6,
        collection_policy=WindowPolicy.SINCE_LAST_SUCCESS,
    )
    due = schedule.next_run_at
    cutoff = due - timedelta(hours=12)
    revision = revision_from_schedule(schedule, 1)
    async with container.session_factory() as session:
        ledger = SqlSubscriptionEditionRepository(session)
        await ledger.save_lineage(
            SubscriptionLineage(
                subscription_id=schedule.id,
                compatibility_fingerprint=revision.compatibility_fingerprint,
                analytical_baseline_version_id=None,
                covered_intervals=(ObservationInterval(cutoff - timedelta(days=1), cutoff),),
                complete_cutoff=cutoff,
                updated_at=container.clock.now(),
            ),
            expected_revision=None,
        )
        await session.commit()
    container.clock.advance(due - container.clock.now() + timedelta(minutes=1))
    assert await container.schedule_runner.run_once() == 1
    async with container.session_factory() as session:
        edition = await SqlSubscriptionEditionRepository(session).active(schedule.id)
    assert edition is not None
    assert edition.requested == ObservationInterval(cutoff - timedelta(hours=3), due)


async def test_newer_complete_baseline_skips_covered_old_slots_without_a_job(
    container: Container, user: User
) -> None:
    schedule = await _local_schedule(
        container,
        user,
        timezone="UTC",
        local_hour=6,
        collection_policy=WindowPolicy.SINCE_LAST_SUCCESS,
    )
    first = schedule.next_run_at
    covering_due = first + timedelta(days=5)
    request_interval = ObservationInterval(first - timedelta(days=1), covering_due)
    revision = revision_from_schedule(schedule, 1)
    report_id, version_id = uuid4(), uuid4()
    now = container.clock.now()
    async with container.session_factory() as session:
        session.add(
            ReportRow(
                id=report_id,
                template="intsum",
                title="Newer baseline",
                scope={},
                period_from=request_interval.start,
                period_to=request_interval.end,
                data_cutoff=covering_due,
                status="ready",
                created_by=user.id,
                created_at=now,
            )
        )
        session.add(
            ReportVersionRow(
                id=version_id,
                report_id=report_id,
                number=1,
                status="ready",
                body={},
                findings=[],
                evidence=[],
                quality={},
                markdown="",
                model="fixture",
                latency_ms=0,
                attempts=1,
                created_at=now,
            )
        )
        await session.flush()
        ledger = SqlSubscriptionEditionRepository(session)
        await ledger.add_revision(revision)
        covering = await ledger.reserve(
            SubscriptionEdition(
                id=scheduled_edition_id(schedule.id, covering_due),
                subscription_id=schedule.id,
                trigger=EditionTrigger.SCHEDULED,
                due_at_utc=covering_due,
                request_uuid=None,
                frozen_revision=1,
                requested=request_interval,
                effective_intervals=(),
                gaps=(),
                compatibility_fingerprint=revision.compatibility_fingerprint,
                baseline_version_id=None,
                workflow=EditionWorkflow.PENDING,
                report_quality=EditionQuality.ABSENT,
                coverage=EditionCoverage.UNKNOWN,
                created_at=now,
                updated_at=now,
            )
        )
        await ledger.advance(
            replace(
                covering,
                workflow=EditionWorkflow.COMPLETED,
                report_quality=EditionQuality.READY,
                coverage=EditionCoverage.COMPLETE_FOR_PLAN,
                effective_intervals=(request_interval,),
                report_id=report_id,
                version_id=version_id,
                revision=2,
            ),
            expected_revision=1,
        )
        await ledger.save_lineage(
            SubscriptionLineage(
                subscription_id=schedule.id,
                compatibility_fingerprint=revision.compatibility_fingerprint,
                analytical_baseline_version_id=version_id,
                covered_intervals=(request_interval,),
                complete_cutoff=covering_due,
                updated_at=now,
            ),
            expected_revision=None,
        )
        await session.commit()
    container.clock.advance(covering_due - container.clock.now() + timedelta(minutes=1))
    assert await container.schedule_runner.run_once() == 0
    async with container.session_factory() as session:
        editions = await SqlSubscriptionEditionRepository(session).history(schedule.id)
        current = await container.repositories(session).schedules.get(schedule.id)
    assert current is not None and current.next_run_at == covering_due + timedelta(days=1)
    assert len(editions) == 6
    assert all(
        edition.covered_by_edition_id == covering.id
        for edition in editions
        if edition.workflow is EditionWorkflow.SKIPPED
    )
