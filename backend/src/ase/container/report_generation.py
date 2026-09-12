"""Construct the shared report pipeline with optional durable call accounting."""

from typing import TYPE_CHECKING, cast

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.feeds.google_news_links import GoogleNewsUrlResolver
from ase.application.ports.llm import LlmGateway, LlmUsageRepository
from ase.application.reports.fresh_web_research import FreshWebResearch
from ase.application.reports.generate import GenerateReportUseCase
from ase.container.research import private_research_store

if TYPE_CHECKING:
    from ase.container import Container


class ReportGenerationWiring:
    def generate_report(
        self,
        session: AsyncSession,
        *,
        gateway: LlmGateway | None = None,
        usage: LlmUsageRepository | None = None,
        web_research: FreshWebResearch | None = None,
    ) -> GenerateReportUseCase:
        container = cast("Container", self)
        r = container.repositories(session)
        return GenerateReportUseCase(
            store=container.store,
            research=container.research,
            web_research=web_research if web_research is not None else container.fresh_web_research,
            research_inputs=container.research_inputs,
            private_store_factory=private_research_store,
            source_profiles=container.source_profiles,
            countries=container.countries,
            conflicts=container.conflicts,
            plans=r.plans,
            aois=r.aois,
            backgrounds={
                "aviation_activity": lambda: container.aviation_background(session),
                "maritime_activity": container._maritime_background,
                "cyber_summary": container._cyber_background,
            },
            llm_profiles=r.llm_profiles,
            llm_bindings=r.llm_bindings,
            usage=usage if usage is not None else r.llm_usage,
            cipher=container.cipher,
            gateway=gateway if gateway is not None else container.llm,
            reports=r.reports,
            map_views=r.map_views,
            claims=r.claims,
            clock=container.clock,
            limiter=container.limiter,
            limits=container.limits,
            auditor=container._auditor(r),
            uow=r.uow,
            url_resolver=GoogleNewsUrlResolver(),
            access=container.access_policy(session),
            projector=container.internal_report_projector,
        )
