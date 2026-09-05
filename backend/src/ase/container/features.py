"""Use-case factories for reports, trackers and direction, mixed into the Container."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from ase.application.direction.areas import CreateAoiUseCase, DeleteAoiUseCase, ListAoisUseCase
from ase.application.direction.plans import (
    CreatePlanUseCase,
    DeletePlanUseCase,
    ListPlansUseCase,
    PlanEvidenceUseCase,
    UpdatePlanUseCase,
)
from ase.application.reports.access import (
    DeleteReportUseCase,
    GetReportUseCase,
    ListReportsUseCase,
)
from ase.application.reports.archiving import archive_evidence
from ase.application.reports.generate import GenerateReportUseCase
from ase.application.trackers.aviation import (
    AviationService,
    background,
)
from ase.application.trackers.boards import TrackerService
from ase.application.trackers.modules import ModuleService, cyber_summary, maritime_summary
from ase.domain.report_records import ReportVersion

if TYPE_CHECKING:
    from collections.abc import Mapping

    from sqlalchemy.ext.asyncio import async_sessionmaker

    from ase.adapters.store.memory import InMemoryEventStore
    from ase.application.auditing import Auditor
    from ase.application.dto import RateLimits
    from ase.application.ports.archive import Archiver
    from ase.application.ports.geo import CountryDirectory
    from ase.application.ports.llm import LlmGateway, SecretCipher
    from ase.application.ports.services import Clock, RateLimiter
    from ase.application.ports.trackers import ConflictDirectory
    from ase.application.trackers.aviation import WatchedArea
    from ase.container import Repositories
    from ase.domain.aviation import JamMap
    from ase.domain.grading import SourceProfile
    from ase.infrastructure.settings import Settings

log = structlog.get_logger(__name__)


class FeatureWiring:
    """Factories that need the core container's services; typed through the Container."""

    if TYPE_CHECKING:
        # The core defines these; declaring them here lets the mixin be type-checked alone.
        settings: Settings
        clock: Clock
        limiter: RateLimiter
        limits: RateLimits
        session_factory: async_sessionmaker[AsyncSession]
        store: InMemoryEventStore
        countries: CountryDirectory
        conflicts: ConflictDirectory
        cipher: SecretCipher
        llm: LlmGateway
        source_profiles: Mapping[str, SourceProfile]
        archiver: Archiver
        jam: JamMap
        watch_areas: tuple[WatchedArea, ...]

        def repositories(self, session: AsyncSession) -> Repositories: ...
        def _auditor(self, repos: Repositories) -> Auditor: ...

    async def archive_report_version(self, version: ReportVersion) -> None:
        """Background job after generation: preserve the URLs the version cites."""
        try:
            async with self.session_factory() as session:
                r = self.repositories(session)
                await archive_evidence(self.archiver, r.reports, r.uow, version)
        except Exception:
            log.warning("archive.job_failed", report_version=str(version.id), exc_info=True)

    def generate_report(self, session: AsyncSession) -> GenerateReportUseCase:
        r = self.repositories(session)
        return GenerateReportUseCase(
            store=self.store,
            source_profiles=self.source_profiles,
            countries=self.countries,
            conflicts=self.conflicts,
            plans=r.plans,
            aois=r.aois,
            backgrounds={
                "aviation_activity": lambda: self.aviation_background(session),
                "maritime_activity": self._maritime_background,
                "cyber_summary": self._cyber_background,
            },
            llm_profiles=r.llm_profiles,
            usage=r.llm_usage,
            cipher=self.cipher,
            gateway=self.llm,
            reports=r.reports,
            clock=self.clock,
            limiter=self.limiter,
            limits=self.limits,
            auditor=self._auditor(r),
            uow=r.uow,
        )

    def trackers(self) -> TrackerService:
        return TrackerService(self.store, self.conflicts, self.clock)

    def modules(self) -> ModuleService:
        return ModuleService(self.store, self.clock)

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
        return CreateAoiUseCase(r.aois, self.clock, self._auditor(r), r.uow)

    def list_aois(self, session: AsyncSession) -> ListAoisUseCase:
        return ListAoisUseCase(self.repositories(session).aois)

    def delete_aoi(self, session: AsyncSession) -> DeleteAoiUseCase:
        r = self.repositories(session)
        return DeleteAoiUseCase(r.aois, self._auditor(r), r.uow)

    def create_plan(self, session: AsyncSession) -> CreatePlanUseCase:
        r = self.repositories(session)
        return CreatePlanUseCase(r.plans, r.aois, self.clock, self._auditor(r), r.uow)

    def update_plan(self, session: AsyncSession) -> UpdatePlanUseCase:
        r = self.repositories(session)
        return UpdatePlanUseCase(r.plans, r.aois, self.clock, self._auditor(r), r.uow)

    def list_plans(self, session: AsyncSession) -> ListPlansUseCase:
        return ListPlansUseCase(self.repositories(session).plans)

    def delete_plan(self, session: AsyncSession) -> DeletePlanUseCase:
        r = self.repositories(session)
        return DeletePlanUseCase(r.plans, self._auditor(r), r.uow)

    def plan_evidence(self, session: AsyncSession) -> PlanEvidenceUseCase:
        r = self.repositories(session)
        return PlanEvidenceUseCase(r.plans, r.aois, self.store, self.clock)

    def list_reports(self, session: AsyncSession) -> ListReportsUseCase:
        return ListReportsUseCase(self.repositories(session).reports)

    def get_report(self, session: AsyncSession) -> GetReportUseCase:
        return GetReportUseCase(self.repositories(session).reports)

    def delete_report(self, session: AsyncSession) -> DeleteReportUseCase:
        r = self.repositories(session)
        return DeleteReportUseCase(r.reports, self._auditor(r), r.uow)
