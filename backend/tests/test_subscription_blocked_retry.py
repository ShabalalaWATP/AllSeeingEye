"""A budget-blocked edition holding a job is probed hourly and resumes when room returns."""

from datetime import timedelta
from uuid import uuid4

from ase.adapters.persistence.llm import SqlLlmUsageRepository
from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.container.report_job_worker import failure_code
from ase.container.subscription_retry_orchestration import SubscriptionRetryOrchestrator
from ase.domain.ai_usage import AiAllowanceExceeded
from ase.domain.errors import Forbidden
from ase.domain.llm import LlmUsage
from ase.domain.subscription_editions import EditionWorkflow
from ase.domain.subscription_monthly_budget import (
    MonthlyBudgetExhausted,
    MonthlyBudgetPolicy,
    MonthlyLimit,
    utc_month,
)
from test_subscription_retry_worker import _claim, _queued


async def _blocked(container, user, error: Exception):
    _, edition, original = await _queued(container, user)
    claimed = await _claim(container, edition.id, original.id)
    await SubscriptionRetryOrchestrator(container).pause(claimed, failure_code(error), error)
    return edition.id, original.id


async def _state(container, edition_id, job_id):
    async with container.session_factory() as session:
        edition = await SqlSubscriptionEditionRepository(session).get(edition_id)
        job = await SqlReportJobRepository(session).get(job_id)
    assert edition is not None and job is not None
    return edition, job


async def test_monthly_block_waits_for_the_month_rollover_then_resumes(container, user):
    container.monthly_budget_policy = MonthlyBudgetPolicy(owner=MonthlyLimit(1, 100))
    edition_id, job_id = await _blocked(container, user, MonthlyBudgetExhausted())
    async with container.session_factory() as session:
        await SqlLlmUsageRepository(session).add(
            LlmUsage(
                at=container.clock.now(),
                profile_id=uuid4(),
                user_id=user.id,
                purpose="report-job",
                ok=True,
                latency_ms=1.0,
                completion_tokens=40,
            )
        )
        await session.commit()
    retry = SubscriptionRetryOrchestrator(container)
    edition, job = await _state(container, edition_id, job_id)
    assert edition.workflow is EditionWorkflow.BLOCKED and job.error == "monthly_budget"

    await retry.resume_due()  # Not yet due: the probe waits an hour.
    unchanged, _ = await _state(container, edition_id, job_id)
    assert unchanged.revision == edition.revision

    container.clock.advance(timedelta(hours=1, minutes=1))
    await retry.resume_due()  # Due, but the owner's month is still exhausted.
    postponed, job = await _state(container, edition_id, job_id)
    assert postponed.workflow is EditionWorkflow.BLOCKED and job.status == "paused"
    assert postponed.revision == edition.revision + 1
    assert postponed.updated_at == container.clock.now()

    _, month_end = utc_month(container.clock.now())
    container.clock.advance(month_end - container.clock.now() + timedelta(minutes=1))
    await retry.resume_due()
    resumed, job = await _state(container, edition_id, job_id)
    assert resumed.workflow is EditionWorkflow.QUEUED and resumed.safe_reason is None
    assert job.status == "queued" and job.error is None


async def test_ai_allowance_block_is_probed_and_resumes_the_same_job(container, user):
    edition_id, job_id = await _blocked(container, user, AiAllowanceExceeded())
    edition, job = await _state(container, edition_id, job_id)
    assert edition.workflow is EditionWorkflow.BLOCKED
    assert edition.safe_reason == job.error == "ai_allowance_exhausted"
    container.clock.advance(timedelta(hours=1, minutes=1))
    await SubscriptionRetryOrchestrator(container).resume_due()
    resumed, job = await _state(container, edition_id, job_id)
    assert resumed.workflow is EditionWorkflow.QUEUED and resumed.job_id == job_id
    assert job.status == "queued"


async def test_access_blocks_need_a_person_and_are_never_probed(container, user):
    edition_id, job_id = await _blocked(container, user, Forbidden())
    blocked, _ = await _state(container, edition_id, job_id)
    assert blocked.workflow is EditionWorkflow.BLOCKED and blocked.safe_reason == "scope_revoked"
    container.clock.advance(timedelta(hours=2))
    await SubscriptionRetryOrchestrator(container).resume_due()
    unchanged, job = await _state(container, edition_id, job_id)
    assert unchanged.revision == blocked.revision and job.status == "paused"
