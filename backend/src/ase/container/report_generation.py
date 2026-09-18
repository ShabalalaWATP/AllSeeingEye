"""Construct the shared report pipeline with optional durable call accounting."""

from typing import TYPE_CHECKING, cast

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.feeds.google_news_links import GoogleNewsUrlResolver
from ase.adapters.geo.area_geography import PackagedAreaGeography
from ase.application.ports.llm import LlmGateway, LlmUsageRepository
from ase.application.reports.area_context import AreaContextService
from ase.application.reports.fresh_web_research import FreshWebResearch
from ase.application.reports.generate import GenerateReportUseCase
from ase.application.reports.original_followthrough import OriginalFollowThrough
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
        original_followthrough: OriginalFollowThrough | None = None,
    ) -> GenerateReportUseCase:
        container = cast("Container", self)
        r = container.repositories(session)
        return GenerateReportUseCase(
            store=container.store,
            research=container.research,
            web_research=web_research if web_research is not None else container.fresh_web_research,
            original_followthrough=original_followthrough,
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
            ai_usage=container.ai_usage_accounting if gateway is None else None,
            embedding_ai_usage=container.ai_usage_accounting,
            embeddings=container.embedding_gateway,
            area_context=AreaContextService(PackagedAreaGeography(), r.baselines, container.jam),
        )
