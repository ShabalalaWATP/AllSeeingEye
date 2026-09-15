"""Run a leased report against frozen inputs and publish it in one final transaction."""

from dataclasses import replace
from typing import TYPE_CHECKING
from uuid import UUID

from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.application.dto import RequestContext
from ase.application.report_jobs.accounting import apply_usage
from ase.application.report_jobs.budget import ReportCallBudget
from ase.application.report_jobs.fresh_web_allocation import WEB_PLAN_KEY
from ase.application.reports.fresh_web_research import FreshWebResearch
from ase.application.reports.save_production import SaveProduction
from ase.container.report_job_checkpoints import ReportJobCheckpoints
from ase.container.report_job_gateways import bind_report_job_gateways
from ase.container.report_original_followthrough import make_original_followthrough
from ase.container.report_original_publication import link_original_followup
from ase.container.subscription_publication import publish_subscription_edition
from ase.domain.llm import LlmUsage
from ase.domain.report_jobs import ReportJob
from ase.domain.report_records import ReportRecord
from ase.domain.reports import ReportStatus
from ase.domain.research_runs import ResearchStage

if TYPE_CHECKING:
    from ase.container import Container


class CheckpointedUsage:
    """The durable call ledger already records each provider call transactionally."""

    async def add(self, usage: LlmUsage) -> None:
        pass

    async def list_recent(self, limit: int) -> list[LlmUsage]:
        return []


async def execute_job(
    container: "Container", stored: ReportJob, checkpoints: ReportJobCheckpoints
) -> None:
    async with container.session_factory() as session:
        job, routing = await container.report_job_gate(session, stored)
        # Background authorisation uses the current owner independently of browser sessions.
        job = replace(
            job,
            report_id=stored.report_id,
            version_id=stored.version_id,
            request=replace(job.request, automation=True),
        )
        await session.rollback()
        if job.request.research_mode is not None:
            await checkpoints.reconcile_open_source_operations(job.request.research_mode)
        budget = ReportCallBudget(checkpoints.mutate, checkpoints.check, profile_id=job.profile.id)
        gateway, web_gateway = await bind_report_job_gateways(
            routing,
            container.cipher,
            container.llm,
            container.web_search_gateway,
            budget,
            ai_usage=container.ai_usage_accounting,
            owner_id=job.actor.id,
            team_id=stored.team_id,
        )
        generator = container.generate_report(
            session,
            gateway=gateway,
            usage=CheckpointedUsage(),
            web_research=FreshWebResearch(
                web_gateway,
                container.source_admission,
                container.clock,
                container.limiter,
                allocation_plan=stored.payload.get(WEB_PLAN_KEY),
            ),
            original_followthrough=(
                make_original_followthrough(container, stored, checkpoints)
                if checkpoints.source_phase_enabled
                else None
            ),
        )

        async def progress(stage: ResearchStage) -> None:
            await checkpoints.mutate(lambda payload: payload.update(stage=stage.value))

        result = await generator.produce_prepared(
            job,
            routing,
            checkpoints=checkpoints,
            progress=progress,
            before_persist=checkpoints.check,
        )
        if stored.brief_id is not None:
            result = replace(
                result,
                version=replace(
                    result.version,
                    brief_id=stored.brief_id,
                    brief_revision=stored.brief_revision,
                ),
            )
        if result.version.status is ReportStatus.FAILED:
            raise ValueError("Report validation did not complete")
        if result.version.id != stored.version_id or result.version.report_id != stored.report_id:
            raise ValueError("Report identifiers changed during generation")
        await session.rollback()
        async with container.source_admission.guard():
            # No lock is held across model calls. SaveProduction acquires current account locks.
            repos = container.repositories(session)
            current = await SqlReportJobRepository(session).get(stored.id)
            if current is None:
                raise ValueError("The report job no longer exists")
            apply_usage(result.version, current.payload)

            async def fence() -> None:
                current = await SqlReportJobRepository(session).get(stored.id)
                if current is None:
                    raise ValueError("The report job no longer exists")
                await checkpoints.finish(
                    session,
                    current.payload,
                    needs_review=result.version.status is ReportStatus.NEEDS_REVIEW,
                )
                access = await container.access_policy(session).background(
                    stored.owner_id, stored.team_id, for_update=True
                )
                await publish_subscription_edition(
                    session,
                    stored,
                    result.version,
                    access,
                    container.clock.now(),
                    research_required=job.request.research_mode is not None,
                )
                await link_original_followup(session, container, stored, result.version)

            record = ReportRecord(
                id=stored.report_id,
                template=job.template.id,
                title=job.title,
                scope=dict(job.scope),
                period_from=job.period_from,
                period_to=job.period_to,
                data_cutoff=result.version.data_cutoff or job.now,
                status=result.version.status,
                created_by=stored.owner_id,
                created_at=job.now,
                latest_version=1,
                team_id=stored.team_id,
            )
            await SaveProduction(
                repos.reports,
                repos.claims,
                container.access_policy(session),
                container._auditor(repos),
                repos.uow,
            ).save(
                job.actor,
                record,
                result,
                RequestContext(),
                creating=True,
                automation=True,
                before_commit=fence,
            )


async def already_published(container: "Container", job_id: UUID) -> bool:
    """A lost commit acknowledgement must never cause a second report insertion."""
    async with container.session_factory() as session:
        stored = await SqlReportJobRepository(session).get(job_id)
        if stored is None or stored.status not in {"completed", "needs_review"}:
            return False
        version = await container.repositories(session).reports.get_version(stored.report_id, 1)
        return version is not None and version.id == stored.version_id
