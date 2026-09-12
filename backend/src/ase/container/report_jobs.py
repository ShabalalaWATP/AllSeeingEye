"""Composition root for authenticated report admission and durable background work."""

import asyncio
from functools import cached_property
from typing import TYPE_CHECKING, cast

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.application.daily_briefing import DailyBriefingService
from ase.application.model_routing import RoleProfiles
from ase.application.report_jobs.service import PrepareJob, ReportJobService
from ase.application.report_jobs.snapshots import freeze_job
from ase.application.reports.production_types import Job
from ase.container.report_job_gate import check_job, release_job
from ase.container.report_job_worker import ReportJobWorker
from ase.container.research import private_research_store
from ase.domain.report_jobs import ReportJob

if TYPE_CHECKING:
    from ase.container import Container


class ReportJobWiring:
    @cached_property
    def daily_briefing_admission(self) -> asyncio.Lock:
        # Single-process report workers: keep day-boundary admissions serial too.
        return asyncio.Lock()

    def daily_briefing(self, session: AsyncSession) -> DailyBriefingService:
        container = cast("Container", self)
        return DailyBriefingService(
            container.report_jobs(session),
            SqlReportJobRepository(session),
            container.repositories(session).uow,
            container.clock,
            self.daily_briefing_admission,
        )

    @cached_property
    def report_job_worker(self) -> ReportJobWorker:
        return ReportJobWorker(cast("Container", self))

    async def report_job_gate(
        self, session: AsyncSession, stored: ReportJob
    ) -> tuple[Job, RoleProfiles]:
        return await check_job(cast("Container", self), session, stored)

    def report_jobs(
        self, session: AsyncSession, *, prepare_job: PrepareJob | None = None
    ) -> ReportJobService:
        container = cast("Container", self)
        repos = container.repositories(session)

        async def strict(stored: ReportJob) -> None:
            await container.report_job_gate(session, stored)

        async def release(stored: ReportJob) -> None:
            await release_job(container, session, stored)

        return ReportJobService(
            repo=SqlReportJobRepository(session),
            access=container.access_policy(session),
            uow=repos.uow,
            clock=container.clock,
            prepare_job=prepare_job or container.generate_report(session).prepare_job,
            freeze=lambda job, routing: freeze_job(
                job, routing, container.source_profiles, private_research_store
            ),
            check_job=release,
            check_resume=strict,
            cancel=container.report_job_worker.cancel,
            source_guard=container.source_admission.guard,
        )
