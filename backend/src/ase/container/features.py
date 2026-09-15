"""Use-case factories for reports, trackers and direction, mixed into the Container."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.feeds.mastodon import load_watch
from ase.adapters.geo.infrastructure import public_infrastructure
from ase.adapters.llm.translator import LlmTranslator
from ase.adapters.persistence.selected_index_acquisition import SqlSelectedIndexAcquisitionStore
from ase.adapters.persistence.social import SqlSocialActivity, SqlSocialTerms
from ase.adapters.persistence.teams import SqlTeamRepository
from ase.adapters.persistence.warning import SqlWarningStore
from ase.adapters.research.selected_event_cache import USGS_SELECTED_POLICY, PublicEventCachePages
from ase.application.direction.areas import CreateAoiUseCase, DeleteAoiUseCase, ListAoisUseCase
from ase.application.direction.plans import (
    CreatePlanUseCase,
    DeletePlanUseCase,
    ListPlansUseCase,
    PlanEvidenceUseCase,
    UpdatePlanUseCase,
)
from ase.application.dto import RequestContext
from ase.application.model_routing import ModelRouting
from ase.application.reports.request import ReportRequest
from ase.application.reports.templates import TEMPLATES
from ase.application.schedules.manage import (
    CreateScheduleUseCase,
    DeleteScheduleUseCase,
    ListSchedulesUseCase,
    UpdateScheduleUseCase,
)
from ase.application.schedules.runner import ScheduleRunner
from ase.application.schedules.selected_index_acquisition import SelectedIndexAcquisition
from ase.application.teams.service import TeamService
from ase.application.trackers.aviation import (
    AviationService,
    background,
)
from ase.application.trackers.boards import TrackerService
from ase.application.trackers.modules import ModuleService, cyber_summary, maritime_summary
from ase.application.trackers.social import SocialMonitor, SocialService
from ase.application.translate.queue import TranslationQueue
from ase.application.warning.alerts import AcknowledgeAlertUseCase, ListAlertsUseCase
from ase.application.warning.evaluator import IndicatorEvaluator
from ase.application.warning.indicators import (
    CreateIndicatorUseCase,
    DeleteIndicatorUseCase,
    ListIndicatorsUseCase,
    UpdateIndicatorUseCase,
)
from ase.container.reporting import ReportWiring
from ase.container.subscription_enqueue import SubscriptionAdmission
from ase.domain.errors import NoModelAvailable
from ase.domain.llm import LlmProfile, LlmRole, LlmUsage
from ase.domain.warning import Alert, Indicator

if TYPE_CHECKING:
    import asyncio
    from collections.abc import Mapping

    from sqlalchemy.ext.asyncio import async_sessionmaker

    from ase.adapters.store.memory import InMemoryEventStore
    from ase.application.auditing import Auditor
    from ase.application.dto import RateLimits
    from ase.application.feeds.health import HealthRegistry
    from ase.application.ports.archive import Archiver
    from ase.application.ports.embeddings import EmbeddingGateway
    from ase.application.ports.feeds import EventBus
    from ase.application.ports.geo import CountryDirectory
    from ase.application.ports.llm import LlmGateway, SecretCipher
    from ase.application.ports.services import Clock, RateLimiter
    from ase.application.ports.trackers import ConflictDirectory
    from ase.application.ports.warning import AlertNotifier
    from ase.application.trackers.aviation import WatchedArea
    from ase.container import Container, Repositories
    from ase.domain.aviation import JamMap
    from ase.domain.grading import SourceProfile
    from ase.infrastructure.settings import Settings

log = structlog.get_logger(__name__)


class FeatureWiring(ReportWiring):
    """Factories that need the core container's services; typed through the Container."""

    if TYPE_CHECKING:
        # The core defines these; declaring them here lets the mixin be type-checked alone.
        settings: Settings
        clock: Clock
        limiter: RateLimiter
        limits: RateLimits
        session_factory: async_sessionmaker[AsyncSession]
        store: InMemoryEventStore
        health: HealthRegistry
        countries: CountryDirectory
        conflicts: ConflictDirectory
        cipher: SecretCipher
        llm: LlmGateway
        embedding_gateway: EmbeddingGateway
        embedding_lock: asyncio.Lock
        source_profiles: Mapping[str, SourceProfile]
        archiver: Archiver
        notifier: AlertNotifier
        bus: EventBus
        jam: JamMap
        watch_areas: tuple[WatchedArea, ...]

        def repositories(self, session: AsyncSession) -> Repositories: ...
        def _auditor(self, repos: Repositories) -> Auditor: ...

    def teams(self, session: AsyncSession) -> TeamService:
        repos = self.repositories(session)
        return TeamService(
            SqlTeamRepository(session), repos.users, self.clock, self._auditor(repos), repos.uow
        )

    def trackers(self) -> TrackerService:
        return TrackerService(self.store, self.conflicts, self.clock)

    def modules(self) -> ModuleService:
        return ModuleService(self.store, self.clock)

    def social(self) -> SocialService:
        terms = SqlSocialTerms(
            self.session_factory,
            [tag for _, tags in load_watch() for tag in tags],
            self.access_policy,
        )
        return SocialService(self.store, terms, SqlSocialActivity(self.session_factory), self.clock)

    def build_social_monitor(self) -> SocialMonitor:
        terms = SqlSocialTerms(
            self.session_factory,
            [tag for _, tags in load_watch() for tag in tags],
            self.access_policy,
        )
        return SocialMonitor(self.store, terms, SqlSocialActivity(self.session_factory), self.clock)

    def aviation(self) -> AviationService:
        return AviationService(self.store, self.jam, self.clock, self.watch_areas)

    async def _maritime_background(self) -> str:
        return maritime_summary(self.modules().maritime_board())

    async def _cyber_background(self) -> str:
        return cyber_summary(self.modules().cyber_board())

    async def aviation_background(self, session: AsyncSession) -> str:
        """The aviation board as a paragraph for the aviation report's background."""
        return await background(self.aviation(), self.repositories(session).baselines)

    def create_aoi(self, session: AsyncSession) -> CreateAoiUseCase:
        r = self.repositories(session)
        return CreateAoiUseCase(
            r.aois, self.clock, self._auditor(r), r.uow, self.access_policy(session)
        )

    def list_aois(self, session: AsyncSession) -> ListAoisUseCase:
        return ListAoisUseCase(self.repositories(session).aois, self.access_policy(session))

    def delete_aoi(self, session: AsyncSession) -> DeleteAoiUseCase:
        r = self.repositories(session)
        return DeleteAoiUseCase(r.aois, self._auditor(r), r.uow, self.access_policy(session))

    def create_plan(self, session: AsyncSession) -> CreatePlanUseCase:
        r = self.repositories(session)
        return CreatePlanUseCase(
            r.plans, r.aois, self.clock, self._auditor(r), r.uow, self.access_policy(session)
        )

    def update_plan(self, session: AsyncSession) -> UpdatePlanUseCase:
        r = self.repositories(session)
        return UpdatePlanUseCase(
            r.plans, r.aois, self.clock, self._auditor(r), r.uow, self.access_policy(session)
        )

    def list_plans(self, session: AsyncSession) -> ListPlansUseCase:
        return ListPlansUseCase(self.repositories(session).plans, self.access_policy(session))

    def delete_plan(self, session: AsyncSession) -> DeletePlanUseCase:
        r = self.repositories(session)
        return DeletePlanUseCase(r.plans, self._auditor(r), r.uow, self.access_policy(session))

    def plan_evidence(self, session: AsyncSession) -> PlanEvidenceUseCase:
        r = self.repositories(session)
        return PlanEvidenceUseCase(
            r.plans, r.aois, self.store, self.clock, self.access_policy(session)
        )

    def create_indicator(self, session: AsyncSession) -> CreateIndicatorUseCase:
        r = self.repositories(session)
        return CreateIndicatorUseCase(
            r.indicators,
            r.plans,
            TEMPLATES,
            self.clock,
            self._auditor(r),
            r.uow,
            self.access_policy(session),
        )

    def update_indicator(self, session: AsyncSession) -> UpdateIndicatorUseCase:
        r = self.repositories(session)
        return UpdateIndicatorUseCase(
            r.indicators,
            r.plans,
            TEMPLATES,
            self.clock,
            self._auditor(r),
            r.uow,
            self.access_policy(session),
        )

    def delete_indicator(self, session: AsyncSession) -> DeleteIndicatorUseCase:
        r = self.repositories(session)
        return DeleteIndicatorUseCase(
            r.indicators,
            r.plans,
            TEMPLATES,
            self.clock,
            self._auditor(r),
            r.uow,
            self.access_policy(session),
        )

    def list_indicators(self, session: AsyncSession) -> ListIndicatorsUseCase:
        return ListIndicatorsUseCase(
            self.repositories(session).indicators, self.access_policy(session)
        )

    def list_alerts(self, session: AsyncSession) -> ListAlertsUseCase:
        return ListAlertsUseCase(
            self.repositories(session).alerts, self.clock, self.access_policy(session)
        )

    def acknowledge_alert(self, session: AsyncSession) -> AcknowledgeAlertUseCase:
        r = self.repositories(session)
        return AcknowledgeAlertUseCase(
            r.alerts, self.clock, self._auditor(r), r.uow, self.access_policy(session)
        )

    def build_evaluator(self) -> IndicatorEvaluator:
        return IndicatorEvaluator(
            self.store,
            SqlWarningStore(self.session_factory, self.access_policy),
            self.bus,
            self.notifier,
            self.clock,
            reporter=self.alert_report,
        )

    async def alert_report(self, indicator: Indicator, alert: Alert) -> UUID | None:
        """The report an indicator asked for, produced as its owner; None when that cannot be."""
        if indicator.report_template is None:
            return None
        async with self.session_factory() as session:
            owner = await self.repositories(session).users.get_by_id(indicator.created_by)
            if owner is None or not owner.is_active:
                log.warning("alert_report_skipped", reason="owner unavailable")
                return None
            request = ReportRequest(
                template_id=indicator.report_template,
                country_iso=indicator.countries[0] if len(indicator.countries) == 1 else None,
                window_hours=max(1, -(-indicator.window_minutes // 60)),
                plan_id=indicator.plan_id,
                team_id=indicator.team_id,
                automation=True,
            )
            record, _version = await self.generate_report(session).execute(
                owner, request, RequestContext()
            )
            return record.id

    def create_schedule(self, session: AsyncSession) -> CreateScheduleUseCase:
        r = self.repositories(session)
        return CreateScheduleUseCase(
            r.schedules, r.plans, self.clock, self._auditor(r), r.uow, self.access_policy(session),
            self.conflicts,
        )  # fmt: skip

    def update_schedule(self, session: AsyncSession) -> UpdateScheduleUseCase:
        r = self.repositories(session)
        return UpdateScheduleUseCase(
            r.schedules, r.plans, self.clock, self._auditor(r), r.uow, self.access_policy(session),
            self.conflicts,
        )  # fmt: skip

    def delete_schedule(self, session: AsyncSession) -> DeleteScheduleUseCase:
        r = self.repositories(session)
        return DeleteScheduleUseCase(
            r.schedules, r.plans, self.clock, self._auditor(r), r.uow, self.access_policy(session)
        )

    def list_schedules(self, session: AsyncSession) -> ListSchedulesUseCase:
        return ListSchedulesUseCase(
            self.repositories(session).schedules, self.access_policy(session)
        )

    def build_schedule_runner(self) -> ScheduleRunner:
        selected_index = SelectedIndexAcquisition(
            SqlSelectedIndexAcquisitionStore(self.session_factory, self.access_policy),
            ((USGS_SELECTED_POLICY, PublicEventCachePages(self.store, self.health)),),
            self.source_admission,
            self.clock,
        )
        return ScheduleRunner(
            SubscriptionAdmission(cast("Container", self)).tick,
            acquisition_tick=selected_index.tick,
        )

    def build_translation_queue(self) -> TranslationQueue:
        translator = LlmTranslator(
            self._translation_profile, self._translation_usage, self.cipher, self.llm, self.clock
        )
        return TranslationQueue(self.store, self.bus, translator, self.clock)

    async def _translation_profile(self) -> LlmProfile | None:
        async with self.session_factory() as session:
            repos = self.repositories(session)
            try:
                routing = await ModelRouting(repos.llm_profiles, repos.llm_bindings).snapshot(
                    role=LlmRole.TRANSLATION
                )
            except NoModelAvailable:
                return None
            return routing.required(LlmRole.TRANSLATION)

    async def _translation_usage(self, usage: LlmUsage) -> None:
        # No transaction is held open while awaiting the model.
        async with self.session_factory() as session:
            await self.repositories(session).llm_usage.add(usage)
            await session.commit()

    def public_infrastructure(self) -> dict[str, Any]:
        return public_infrastructure()
