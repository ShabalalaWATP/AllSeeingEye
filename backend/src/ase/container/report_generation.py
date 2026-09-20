"""Construct the shared report pipeline with optional durable call accounting."""

from typing import TYPE_CHECKING, cast

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.feeds.google_news_links import GoogleNewsUrlResolver
from ase.adapters.geo.area_geography import PackagedAreaGeography
from ase.application.model_routing import ModelRouting
from ase.application.ports.llm import LlmGateway, LlmUsageRepository
from ase.application.reports.area_context import AreaContextService
from ase.application.reports.authorisation import ReportAuthorisation
from ase.application.reports.automatic_claims import AutomaticClaims
from ase.application.reports.evidence_rerank import EvidenceReranker
from ase.application.reports.fresh_web_research import FreshWebResearch
from ase.application.reports.generate import GenerateReportUseCase
from ase.application.reports.job_preparation import ReportJobBuilder
from ase.application.reports.map_origin import ReportMapOrigin
from ase.application.reports.original_followthrough import OriginalFollowThrough
from ase.application.reports.production import Producer
from ase.application.reports.research_inputs import ReportResearchInputs
from ase.application.reports.save_production import SaveProduction
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
        access = container.access_policy(session)
        selected_gateway = gateway if gateway is not None else container.llm
        map_origin = ReportMapOrigin(access, r.reports, r.map_views)
        backgrounds = {
            "aviation_activity": lambda: container.aviation_background(session),
            "maritime_activity": container._maritime_background,
            "cyber_summary": container._cyber_background,
        }
        producer = Producer(
            store=container.store,
            research=container.research,
            web_research=web_research if web_research is not None else container.fresh_web_research,
            original_followthrough=original_followthrough,
            private_store_factory=private_research_store,
            source_profiles=container.source_profiles,
            usage=usage if usage is not None else r.llm_usage,
            cipher=container.cipher,
            gateway=selected_gateway,
            automatic_claims=AutomaticClaims(
                selected_gateway, container.cipher, container.clock, container.limiter
            ),
            url_resolver=GoogleNewsUrlResolver(),
            projector=container.internal_report_projector,
            # Queued text gateways meter their own calls; embeddings always need accounting.
            ai_usage=container.ai_usage_accounting if gateway is None else None,
            reranker=EvidenceReranker(
                cipher=container.cipher,
                gateway=container.embedding_gateway,
                ai_usage=container.ai_usage_accounting,
            ),
            area_context=AreaContextService(PackagedAreaGeography(), r.baselines, container.jam),
        )
        return GenerateReportUseCase(
            producer=producer,
            builder=ReportJobBuilder(container.countries, container.conflicts, r.aois, backgrounds),
            routing=ModelRouting(r.llm_profiles, r.llm_bindings),
            cipher=container.cipher,
            reports=r.reports,
            clock=container.clock,
            limiter=container.limiter,
            limits=container.limits,
            save=SaveProduction(r.reports, r.claims, access, container._auditor(r), r.uow),
            uow=r.uow,
            map_origin=map_origin,
            authorisation=ReportAuthorisation(
                access, r.reports, r.plans, r.aois, r.uow, map_origin
            ),
            research_inputs=ReportResearchInputs(access, r.reports, container.research_inputs),
        )
