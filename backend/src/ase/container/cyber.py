"""Cyber views and durable private briefings share existing feed and report boundaries."""

from dataclasses import replace
from functools import cached_property
from typing import TYPE_CHECKING, cast

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.cyber_reference import MITRE_ATTACK_SPEC, load_actor_catalogue
from ase.adapters.feeds.cisa_kev import SPEC as KEV_SPEC
from ase.adapters.feeds.cyber import IODA, RANSOMWARE
from ase.adapters.feeds.network_outages import CLOUDFLARE_RADAR, IODA_EVENTS
from ase.adapters.feeds.radar_attack_trends import SPEC as RADAR_ATTACK_SPEC
from ase.adapters.feeds.radar_attack_trends import RadarAttackTrends
from ase.adapters.feeds.rss_seeds_cyber import CYBER_SEEDS
from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.application.cyber import CyberService
from ase.application.cyber_briefing import coverage_note, cyber_briefing_request
from ase.application.daily_briefing import DailyBriefingService
from ase.application.model_routing import RoleProfiles
from ase.application.reports.production_types import Job
from ase.application.reports.request import ReportRequest
from ase.domain.cyber import CyberWindowDays, cyber_window
from ase.domain.cyber_actors import CyberActorCatalogue
from ase.domain.daily_briefing import cyber_briefing_key
from ase.domain.users import User

if TYPE_CHECKING:
    from ase.container import Container


class CyberWiring:
    def initialise_cyber(self) -> None:
        container = cast("Container", self)
        # Register reference provenance and administrative controls, never a live
        # connector or an unimplemented research provider.
        if MITRE_ATTACK_SPEC.id not in container.settings.disabled_feed_ids:
            container.research_sources = (*container.research_sources, MITRE_ATTACK_SPEC)
        container.research_sources = (*container.research_sources, RADAR_ATTACK_SPEC)

    @cached_property
    def radar_attack_trends(self) -> RadarAttackTrends:
        container = cast("Container", self)
        token = container.settings.cloudflare_radar_token
        return RadarAttackTrends(
            container.http,
            container.clock,
            token.get_secret_value() if token else None,
        )

    @cached_property
    def cyber_actors(self) -> CyberActorCatalogue:
        return load_actor_catalogue()

    @cached_property
    def cyber(self) -> CyberService:
        container = cast("Container", self)
        return CyberService(
            container.store,
            container.clock,
            {
                spec.id: spec
                for spec in (
                    KEV_SPEC,
                    RANSOMWARE,
                    IODA,
                    IODA_EVENTS,
                    CLOUDFLARE_RADAR,
                    *(s.spec for s in CYBER_SEEDS),
                )
            },
            container.source_admission,
            container.health,
            self.cyber_actors.actors,
        )

    def cyber_briefing(
        self, session: AsyncSession, days: CyberWindowDays = CyberWindowDays.TWO
    ) -> DailyBriefingService:
        container = cast("Container", self)
        days = cyber_window(days)

        def request_factory() -> ReportRequest:
            request = cyber_briefing_request(days)
            available = {spec.id for spec in container.research_sources}
            return replace(
                request,
                research_source_ids=tuple(
                    key for key in request.research_source_ids or () if key in available
                ),
            )

        async def prepare(actor: User, request: ReportRequest) -> tuple[Job, RoleProfiles]:
            job, routing = await container.generate_report(session).prepare_job(actor, request)
            return replace(
                job, title=f"{int(days)} day cyber threat intelligence briefing"
            ), routing

        return DailyBriefingService(
            container.report_jobs(session, prepare_job=prepare),
            SqlReportJobRepository(session),
            container.repositories(session).uow,
            container.clock,
            container.daily_briefing_admission,
            identity=lambda owner_id, at: cyber_briefing_key(owner_id, at, days),
            request_factory=request_factory,
            coverage_note=coverage_note(days),
        )
