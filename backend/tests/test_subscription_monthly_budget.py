"""UTC-month model allowances use saved reservations, not currency estimates."""

from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from ase.adapters.persistence.llm import SqlLlmUsageRepository
from ase.adapters.persistence.monthly_report_usage import (
    monthly_usage,
    require_admission_room,
)
from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.application.report_jobs.budget import ReportCallBudget
from ase.application.schedules.revision_snapshot import request_from_revision
from ase.container.report_job_checkpoints import ReportJobCheckpoints
from ase.container.report_job_worker import failure_code
from ase.container.subscription_retry_orchestration import SubscriptionRetryOrchestrator
from ase.domain.errors import InvalidRequest
from ase.domain.llm import LlmUsage
from ase.domain.subscription_editions import EditionWorkflow
from ase.domain.subscription_monthly_budget import (
    MonthlyBudgetExhausted,
    MonthlyBudgetPolicy,
    MonthlyLimit,
    MonthlyUsage,
    require_monthly_room,
    utc_month,
)
from ase.infrastructure.settings import Settings
from report_job_helpers import job
from test_subscription_retry_worker import _claim, _in_flight_call, _queued


def test_utc_month_boundaries_and_downward_limits() -> None:
    start, end = utc_month(datetime(2026, 10, 1, 0, 30, tzinfo=timezone(timedelta(hours=1))))
    assert start == datetime(2026, 9, 1, tzinfo=UTC)
    assert end == datetime(2026, 10, 1, tzinfo=UTC)
    assert utc_month(datetime(2026, 12, 31, tzinfo=UTC))[1] == datetime(2027, 1, 1, tzinfo=UTC)
    with pytest.raises(ValueError):
        utc_month(datetime(2026, 9, 1))
    with pytest.raises(ValueError):
        MonthlyBudgetPolicy(owner=MonthlyLimit(801, 1))
    with pytest.raises(ValidationError):
        Settings(_env_file=None, monthly_owner_requests=801)
    require_monthly_room(MonthlyUsage(1, 40), MonthlyLimit(2, 100), output_tokens=60)
    with pytest.raises(MonthlyBudgetExhausted):
        require_monthly_room(MonthlyUsage(1, 40), MonthlyLimit(1, 100), output_tokens=1)


async def test_unknown_reservation_rolls_over_and_settlement_adjusts_dispatch_month(
    container, user
) -> None:
    schedule, edition, original = await _queued(container, user)
    september = datetime(2026, 9, 30, 23, 59, 50, tzinfo=UTC)
    container.clock.advance(september - container.clock.now())
    claimed = await _claim(container, edition.id, original.id)
    assert claimed.lease_token is not None
    container.monthly_budget_policy = MonthlyBudgetPolicy(
        owner=MonthlyLimit(1, 100), subscription=MonthlyLimit(1, 100)
    )
    checkpoints = ReportJobCheckpoints(container, original.id, claimed.lease_token)
    first = _in_flight_call() | {"profile_id": str(uuid4())}
    await checkpoints.mutate(lambda payload: payload["calls"].append(first))
    async with container.session_factory() as session:
        owner, subscription = await monthly_usage(session, user.id, schedule.id, september)
    assert owner == subscription == MonthlyUsage(1, 100)
    invoke = AsyncMock()
    budget = ReportCallBudget(checkpoints.mutate, checkpoints.check, profile_id=uuid4())
    with pytest.raises(MonthlyBudgetExhausted):
        await budget.run(
            request_hash="c" * 64,
            schema="report_section",
            model="fixture-model",
            reserved_output=50,
            invoke=invoke,
        )
    invoke.assert_not_awaited()

    container.clock.advance(timedelta(seconds=20))
    october = container.clock.now()
    second = _in_flight_call() | {"profile_id": str(uuid4()), "request_hash": "b" * 64}
    await checkpoints.mutate(lambda payload: payload["calls"].append(second))
    await checkpoints.mutate(
        lambda payload: payload["calls"][0].update(
            status="completed", completion_tokens=40, prompt_tokens=10
        )
    )
    await checkpoints.mutate(
        lambda payload: payload["calls"][1].update(status="uncertain", error="interrupted")
    )
    async with container.session_factory() as session:
        september_owner, september_subscription = await monthly_usage(
            session, user.id, schedule.id, september
        )
        october_owner, october_subscription = await monthly_usage(
            session, user.id, schedule.id, october
        )
        stored = await SqlReportJobRepository(session).get(original.id)
        with pytest.raises(MonthlyBudgetExhausted):
            await require_admission_room(
                session, user.id, schedule.id, october, container.monthly_budget_policy
            )
    assert september_owner == september_subscription == MonthlyUsage(1, 40)
    assert october_owner == october_subscription == MonthlyUsage(1, 100)
    assert stored is not None
    assert stored.payload["calls"][0]["dispatched_at"].startswith("2026-09-30")
    assert stored.payload["calls"][1]["status"] == "uncertain"


async def test_one_off_and_subscription_calls_share_owner_pool(container, user) -> None:
    schedule, edition, original = await _queued(container, user)
    claimed = await _claim(container, edition.id, original.id)
    assert claimed.lease_token is not None
    checkpoints = ReportJobCheckpoints(container, original.id, claimed.lease_token)
    await checkpoints.mutate(
        lambda payload: payload["calls"].append(_in_flight_call() | {"profile_id": str(uuid4())})
    )
    now = container.clock.now()
    one_off_call = _in_flight_call() | {
        "profile_id": str(uuid4()),
        "dispatched_at": now.isoformat(),
    }
    async with container.session_factory() as session:
        await SqlReportJobRepository(session).add(
            job(
                owner_id=user.id,
                created_at=now,
                updated_at=now,
                payload={"schema_version": 1, "calls": [one_off_call]},
            )
        )
        await session.commit()
    async with container.session_factory() as session:
        owner, subscription = await monthly_usage(session, user.id, schedule.id, now)
        assert owner == MonthlyUsage(2, 200)
        assert subscription == MonthlyUsage(1, 100)
        with pytest.raises(MonthlyBudgetExhausted):
            await require_admission_room(
                session,
                user.id,
                None,
                now,
                MonthlyBudgetPolicy(owner=MonthlyLimit(2, 300), subscription=MonthlyLimit(2, 300)),
            )
        with pytest.raises(MonthlyBudgetExhausted):
            await require_admission_room(
                session,
                user.id,
                schedule.id,
                now,
                MonthlyBudgetPolicy(owner=MonthlyLimit(3, 300), subscription=MonthlyLimit(1, 300)),
            )


async def test_owner_fairness_prevents_two_lease_fenced_jobs(container, user) -> None:
    now = container.clock.now()
    values = [
        job(
            owner_id=user.id,
            status="running",
            stage="drafting",
            created_at=now,
            updated_at=now,
            lease_token=uuid4(),
            lease_until=now + timedelta(seconds=45),
            payload={"schema_version": 1, "calls": []},
        )
        for _ in range(2)
    ]
    async with container.session_factory() as session:
        repository = SqlReportJobRepository(session)
        await repository.add(values[0])
        with pytest.raises(IntegrityError):
            await repository.add(values[1])


async def test_paid_one_off_discard_retains_settled_usage_and_uncertain_reservation(
    container, user
) -> None:
    now = container.clock.now()
    known_call = _in_flight_call() | {
        "status": "completed",
        "completion_tokens": 40,
        "profile_id": str(uuid4()),
        "dispatched_at": now.isoformat(),
    }
    uncertain_call = _in_flight_call() | {
        "status": "uncertain",
        "error": "interrupted",
        "profile_id": str(uuid4()),
        "dispatched_at": now.isoformat(),
    }
    unknown_call = _in_flight_call() | {
        "status": "failed",
        "error": "provider_error",
        "profile_id": str(uuid4()),
        "dispatched_at": now.isoformat(),
    }
    values = [
        job(
            owner_id=user.id,
            status="paused",
            stage="paused",
            created_at=now,
            updated_at=now,
            payload={"schema_version": 1, "calls": [call]},
        )
        for call in (known_call, uncertain_call, unknown_call)
    ]
    async with container.session_factory() as session:
        repository = SqlReportJobRepository(session)
        for value in values:
            await repository.add(value)
        await SqlLlmUsageRepository(session).add(
            LlmUsage(
                at=now,
                profile_id=uuid4(),
                user_id=user.id,
                purpose="report-job",
                ok=True,
                latency_ms=1.0,
                completion_tokens=40,
            )
        )
        await SqlLlmUsageRepository(session).add(
            LlmUsage(
                at=now,
                profile_id=uuid4(),
                user_id=user.id,
                purpose="report-job",
                ok=False,
                latency_ms=1.0,
                completion_tokens=None,
                error="provider_error",
            )
        )
        await session.commit()
    async with container.session_factory() as session:
        await container.report_jobs(session).discard(user, values[0].id, check_session=AsyncMock())
    async with container.session_factory() as session:
        owner, _ = await monthly_usage(session, user.id, None, now)
        assert owner == MonthlyUsage(3, 240)
        with pytest.raises(InvalidRequest, match="uncertain"):
            await container.report_jobs(session).discard(
                user, values[1].id, check_session=AsyncMock()
            )
    async with container.session_factory() as session:
        with pytest.raises(InvalidRequest, match="unknown"):
            await container.report_jobs(session).discard(
                user, values[2].id, check_session=AsyncMock()
            )


async def test_worker_monthly_limit_blocks_edition_without_retry(container, user) -> None:
    _, edition, original = await _queued(container, user)
    claimed = await _claim(container, edition.id, original.id)
    error = MonthlyBudgetExhausted()
    await SubscriptionRetryOrchestrator(container).pause(claimed, failure_code(error), error)
    async with container.session_factory() as session:
        current = await SqlSubscriptionEditionRepository(session).get(edition.id)
        job_state = await SqlReportJobRepository(session).get(original.id)
    assert current is not None and job_state is not None
    assert current.workflow is EditionWorkflow.BLOCKED
    assert current.safe_reason == job_state.error == "monthly_budget"
    assert job_state.status == "paused"


async def test_subscription_admission_checks_the_shared_monthly_pool(container, user) -> None:
    schedule, edition, original = await _queued(container, user)
    claimed = await _claim(container, edition.id, original.id)
    assert claimed.lease_token is not None
    container.monthly_budget_policy = MonthlyBudgetPolicy(
        owner=MonthlyLimit(1, 100), subscription=MonthlyLimit(1, 100)
    )
    checkpoints = ReportJobCheckpoints(container, original.id, claimed.lease_token)
    await checkpoints.mutate(
        lambda payload: payload["calls"].append(_in_flight_call() | {"profile_id": str(uuid4())})
    )
    async with container.session_factory() as session:
        revision = await SqlSubscriptionEditionRepository(session).get_revision(
            schedule.id, edition.frozen_revision
        )
        assert revision is not None
        candidate = await container.report_jobs(session).prepare_candidate(
            user, uuid4(), request_from_revision(revision)
        )
        await session.rollback()
    async with container.source_admission.guard(), container.session_factory() as session:
        with pytest.raises(MonthlyBudgetExhausted):
            await container.report_jobs(session).admit_prepared(
                user,
                candidate,
                check_session=AsyncMock(),
                subscription_id=schedule.id,
            )
        await session.rollback()
    async with container.session_factory() as session:
        assert (
            await SqlReportJobRepository(session).get_by_request(user.id, candidate.request_key)
            is None
        )
