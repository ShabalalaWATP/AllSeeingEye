"""Economy reports use the normal durable job boundary and frozen source checks."""

from dataclasses import replace
from functools import cached_property
from typing import TYPE_CHECKING, cast

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.feeds.rss_seeds_economy import ECONOMY_SEEDS
from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.application.daily_briefing import DailyBriefingService
from ase.application.economy_briefing import coverage_note, economy_briefing_request
from ase.application.economy_evidence import economy_evidence
from ase.application.economy_news import EconomyNewsService
from ase.application.model_routing import RoleProfiles
from ase.application.reports.production_types import Job
from ase.application.reports.request import ReportRequest
from ase.application.reports.selection import select_evidence
from ase.application.reports.templates import EvidenceStrategy
from ase.container.research import private_research_store
from ase.domain.daily_briefing import economy_briefing_key
from ase.domain.economy_periods import EconomyWindowDays, economy_window
from ase.domain.events import Category
from ase.domain.users import User

if TYPE_CHECKING:
    from ase.container import Container


class EconomyBriefingWiring:
    @cached_property
    def economy_news(self) -> EconomyNewsService:
        container = cast("Container", self)
        return EconomyNewsService(
            container.store,
            container.clock,
            {seed.spec.id: seed.spec for seed in ECONOMY_SEEDS},
            container.source_admission,
        )

    def economy_briefing(
        self, session: AsyncSession, days: EconomyWindowDays = EconomyWindowDays.TWO
    ) -> DailyBriefingService:
        container = cast("Container", self)
        days = economy_window(days)

        def request_factory() -> ReportRequest:
            request = economy_briefing_request(days)
            available = {spec.id for spec in container.research_sources}
            return replace(
                request,
                research_source_ids=tuple(
                    key for key in request.research_source_ids or () if key in available
                ),
            )

        async def prepare(actor: User, request: ReportRequest) -> tuple[Job, RoleProfiles]:
            # Authorise and release the DB snapshot before bounded public-data work.
            job, routing = await container.generate_report(session).prepare_job(actor, request)
            snapshot = await container.economy.snapshot()
            job = replace(job, now=container.clock.now())
            context = private_research_store()
            context.upsert(economy_evidence(snapshot, container.clock.now()))
            # Dated context can be older than the news window. Only selected bounded
            # evidence persists; its observation/retrieval dates are never rewritten.
            selected = select_evidence(
                context,
                container.source_profiles,
                EvidenceStrategy(frozenset({Category.ECONOMIC}), 8 * 24, 12, 8),
                now=container.clock.now(),
                include_unknown_dates=True,
            )
            return replace(
                job,
                title=f"{int(days)} day economic summary",
                reused_evidence=selected.items,
            ), routing

        return DailyBriefingService(
            container.report_jobs(session, prepare_job=prepare),
            SqlReportJobRepository(session),
            container.repositories(session).uow,
            container.clock,
            container.daily_briefing_admission,
            identity=lambda owner_id, at: economy_briefing_key(owner_id, at, days),
            request_factory=request_factory,
            coverage_note=coverage_note(days),
        )
