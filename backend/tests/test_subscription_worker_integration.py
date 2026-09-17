"""Two due slots survive durable job freezing, worker execution and publication."""

import asyncio
import json
from dataclasses import replace
from datetime import timedelta
from unittest.mock import patch

from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.application.report_jobs.service import ReportJobService
from ase.application.schedules.manage import ScheduleInput
from ase.domain.subscription_editions import EditionWorkflow
from feeds_helpers import make_event
from llm_fixture_helpers import seed_legacy_profile
from report_job_api_helpers import JobGateway, job_settings, work
from team_helpers import CONTEXT

__all__ = ["job_settings"]


class ComparisonGateway(JobGateway):
    """A draft an intsum accepts: three judgements and a stated gap, so the edition
    completes and the subscription can adopt it as the comparison baseline."""

    async def complete(self, base_url, key, model, request):
        result = await super().complete(base_url, key, model, request)
        if request.schema_name == "report_context":
            body = json.loads(result.content)
            body["gaps"] = [
                {
                    "text": "No independent confirmation of the instrument readings was found.",
                    "eei": None,
                }
            ]
            return replace(result, content=json.dumps(body))
        if request.schema_name != "report_judgements":
            return result
        body = json.loads(result.content)
        for judgement in body.get("key_judgements", []):
            judgement["statement"] = (
                "We assess it is highly likely that instrument observations "
                "were recorded in Ukraine during the reporting period."
            )
            judgement["change_from_previous"] = "new"
        return replace(result, content=json.dumps(body))


def _evidence(container, prefix):
    container.store.upsert(
        tuple(
            make_event(
                f"{prefix}-{index}",
                # The intsum template expects three organisations. A report that misses
                # that is held for review, and a report held for review is never accepted
                # as the comparison baseline these editions depend on.
                source_id=("usgs_earthquakes", "emsc_earthquakes", "gdacs")[index % 3],
                title=f"Instrument observation {index}",
                summary=(
                    "Instrument observations were recorded in Ukraine during the "
                    "reporting period by a public sensor network."
                ),
                country_iso="UA",
                # A late worker must still select only observations before the
                # original due slot, not events arriving one minute afterwards.
                published_at=container.clock.now() - timedelta(minutes=2),
                observed_at=container.clock.now() - timedelta(minutes=2),
            )
            for index in range(4)
        )
    )


async def test_two_editions_use_frozen_comparison_context_and_one_job_each(container, user):
    await seed_legacy_profile(
        container,
        {
            "name": "Subscription test profile",
            "base_url": "https://model.test/v1",
            "model": "fixture-model",
            "api_key": "synthetic-job-key",
            "roles": ["assessment"],
            "max_output_tokens": 32000,
            "temperature": 0.1,
        },
    )
    gateway = ComparisonGateway()
    container.llm = gateway
    async with container.session_factory() as session:
        schedule = await container.create_schedule(session).execute(
            user,
            # An intelligence report, whose structure this synthetic draft can meet: the
            # subject here is the edition ledger, not how rich the writing is.
            ScheduleInput(name="Daily observation", template_id="intrep", country_iso="UA"),
            CONTEXT,
        )
    container.clock.advance(schedule.next_run_at - container.clock.now() + timedelta(minutes=1))
    _evidence(container, "first")
    assert await container.schedule_runner.run_once() == 1
    assert await container.schedule_runner.run_once() == 0
    await work(container)
    async with container.session_factory() as session:
        ledger = SqlSubscriptionEditionRepository(session)
        first = (await ledger.history(schedule.id))[0]
        first_job = await SqlReportJobRepository(session).get(first.job_id)
        current = await container.repositories(session).schedules.get(schedule.id)
        assert first_job is not None and current is not None
        assert first.workflow is EditionWorkflow.COMPLETED
        assert first.report_id == first_job.report_id
        assert first.version_id == first_job.version_id
        assert current.baseline_report_id == first.report_id
        assert current.last_version_id == first.version_id
        assert current.seen_content_signatures
        first_report_id = first.report_id
        first_version_id = first.version_id
        next_due = current.next_run_at

    container.clock.advance(next_due - container.clock.now() + timedelta(minutes=1))
    _evidence(container, "second")
    assert await container.schedule_runner.run_once() == 1
    assert await container.schedule_runner.run_once() == 0
    async with container.session_factory() as session:
        second = (await SqlSubscriptionEditionRepository(session).history(schedule.id))[0]
        second_job = await SqlReportJobRepository(session).get(second.job_id)
        assert second_job is not None
        assert second.id != first.id
        assert second.job_request_key != first.job_request_key
        assert second_job.payload["input"]["schema_version"] == 2
        context = second_job.payload["input"]["subscription_context"]
        assert context["report_id"] == str(first_report_id)
        assert context["version"] == 1
        assert context["seen_signatures"]
        restored, _ = await container.report_job_gate(session, second_job)
        assert restored.subscription_baseline is not None
        assert restored.subscription_baseline.id == first_version_id
        assert restored.request.subscription_seen_signatures
    await work(container)
    async with container.session_factory() as session:
        editions = await SqlSubscriptionEditionRepository(session).history(schedule.id)
        assert len(editions) == 2
        jobs = [await SqlReportJobRepository(session).get(item.job_id) for item in editions]
        assert all(item.workflow is EditionWorkflow.COMPLETED for item in editions), [
            (
                item.workflow,
                item.safe_reason,
                job.status if job else None,
                job.error if job else None,
            )
            for item, job in zip(editions, jobs, strict=True)
        ]
        assert editions[0].report_id != editions[1].report_id
        reports = await container.repositories(session).reports.list_recent(10)
        assert len([item for item in reports if item.id in {e.report_id for e in editions}]) == 2


async def test_overlapping_ticks_and_rolled_back_admission_keep_one_slot(container, user):
    await seed_legacy_profile(
        container,
        {
            "name": "Subscription test profile",
            "base_url": "https://model.test/v1",
            "model": "fixture-model",
            "api_key": "synthetic-job-key",
            "roles": ["assessment"],
            "max_output_tokens": 32000,
            "temperature": 0.1,
        },
    )
    async with container.session_factory() as session:
        schedule = await container.create_schedule(session).execute(
            user,
            # An intelligence report, whose structure this synthetic draft can meet: the
            # subject here is the edition ledger, not how rich the writing is.
            ScheduleInput(name="Daily observation", template_id="intrep", country_iso="UA"),
            CONTEXT,
        )
    container.clock.advance(schedule.next_run_at - container.clock.now() + timedelta(minutes=1))
    with patch.object(ReportJobService, "admit_prepared", side_effect=RuntimeError("crash")):
        assert await container.schedule_runner.run_once() == 0
    async with container.session_factory() as session:
        assert await SqlSubscriptionEditionRepository(session).history(schedule.id) == []
        current = await container.repositories(session).schedules.get(schedule.id)
        assert current is not None and current.next_run_at == schedule.next_run_at
    assert (
        sum(
            await asyncio.gather(
                container.schedule_runner.run_once(), container.schedule_runner.run_once()
            )
        )
        == 1
    )
    async with container.session_factory() as session:
        editions = await SqlSubscriptionEditionRepository(session).history(schedule.id)
        assert len(editions) == 1
        job = await SqlReportJobRepository(session).get(editions[0].job_id)
        assert job is not None and job.status == "queued"
