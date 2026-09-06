"""Use-case factories for reports, trackers and direction, mixed into the Container."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.feeds.google_news_links import GoogleNewsUrlResolver
from ase.adapters.persistence.report_search import SqlReportEmbeddingRepository
from ase.adapters.persistence.research_library import SqlResearchLibraryRepository
from ase.adapters.persistence.teams import SqlTeamRepository
from ase.adapters.reports.documents import ReportDocumentRenderer
from ase.adapters.reports.evidence_package import FrozenEvidencePackageRenderer
from ase.application.access import AccessPolicy
from ase.application.reports.access import (
    DeleteReportUseCase,
    GetReportUseCase,
    ListReportsUseCase,
)
from ase.application.reports.archiving import archive_evidence
from ase.application.reports.evidence_package import ExportEvidencePackage
from ase.application.reports.exports import CompareReportsUseCase, ExportReportUseCase
from ase.application.reports.generate import GenerateReportUseCase
from ase.application.reports.search import ReportSearchService
from ase.application.research.library import ResearchLibrary
from ase.application.research.map_views import SavedMapViews
from ase.container.research import private_research_store
from ase.domain.report_records import ReportVersion

if TYPE_CHECKING:
    import asyncio
    from collections.abc import Mapping

    from sqlalchemy.ext.asyncio import async_sessionmaker

    from ase.adapters.store.memory import InMemoryEventStore
    from ase.application.auditing import Auditor
    from ase.application.dto import RateLimits
    from ase.application.ports.archive import Archiver
    from ase.application.ports.embeddings import EmbeddingGateway
    from ase.application.ports.feeds import EventBus
    from ase.application.ports.geo import CountryDirectory
    from ase.application.ports.llm import LlmGateway, SecretCipher
    from ase.application.ports.research import ResearchCollection
    from ase.application.ports.research_inputs import ResearchInputStore
    from ase.application.ports.services import Clock, RateLimiter
    from ase.application.ports.trackers import ConflictDirectory
    from ase.application.ports.warning import AlertNotifier
    from ase.application.trackers.aviation import WatchedArea
    from ase.container import Repositories
    from ase.domain.aviation import JamMap
    from ase.domain.grading import SourceProfile
    from ase.infrastructure.settings import Settings

log = structlog.get_logger(__name__)


class ReportWiring:
    """Session-scoped report production, export and search factories."""

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
        embedding_gateway: EmbeddingGateway
        embedding_lock: asyncio.Lock
        source_profiles: Mapping[str, SourceProfile]
        archiver: Archiver
        notifier: AlertNotifier
        bus: EventBus
        jam: JamMap
        watch_areas: tuple[WatchedArea, ...]
        research: ResearchCollection
        research_inputs: ResearchInputStore

        def repositories(self, session: AsyncSession) -> Repositories: ...
        def _auditor(self, repos: Repositories) -> Auditor: ...

        async def _maritime_background(self) -> str: ...
        async def _cyber_background(self) -> str: ...
        async def aviation_background(self, session: AsyncSession) -> str: ...

    def access_policy(self, session: AsyncSession) -> AccessPolicy:
        return AccessPolicy(self.repositories(session).users, SqlTeamRepository(session))

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
            research=self.research,
            research_inputs=self.research_inputs,
            private_store_factory=private_research_store,
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
            llm_bindings=r.llm_bindings,
            usage=r.llm_usage,
            cipher=self.cipher,
            gateway=self.llm,
            reports=r.reports,
            clock=self.clock,
            limiter=self.limiter,
            limits=self.limits,
            auditor=self._auditor(r),
            uow=r.uow,
            url_resolver=GoogleNewsUrlResolver(),
            access=self.access_policy(session),
        )

    def report_search(self, session: AsyncSession) -> ReportSearchService:
        r = self.repositories(session)
        return ReportSearchService(
            reports=r.reports,
            embeddings=SqlReportEmbeddingRepository(session),
            profiles=r.llm_profiles,
            bindings=r.llm_bindings,
            usage=r.llm_usage,
            cipher=self.cipher,
            gateway=self.embedding_gateway,
            clock=self.clock,
            limiter=self.limiter,
            lock=self.embedding_lock,
            uow=r.uow,
            access=self.access_policy(session),
        )

    def research_library(self, session: AsyncSession) -> ResearchLibrary:
        r = self.repositories(session)
        return ResearchLibrary(
            r.users,
            r.refresh_tokens,
            r.reports,
            SqlResearchLibraryRepository(session),
            self.access_policy(session),
            self.clock,
            self._auditor(r),
            r.uow,
        )

    def saved_map_views(self, session: AsyncSession) -> SavedMapViews:
        r = self.repositories(session)
        return SavedMapViews(
            r.users,
            r.refresh_tokens,
            r.reports,
            r.map_views,
            self.access_policy(session),
            self.clock,
            self._auditor(r),
            r.uow,
        )

    def export_report(self, session: AsyncSession) -> ExportReportUseCase:
        return ExportReportUseCase(self.get_report(session), ReportDocumentRenderer())

    def export_evidence_package(self, session: AsyncSession) -> ExportEvidencePackage:
        return ExportEvidencePackage(self.get_report(session), FrozenEvidencePackageRenderer())

    def compare_reports(self, session: AsyncSession) -> CompareReportsUseCase:
        return CompareReportsUseCase(self.get_report(session))

    def list_reports(self, session: AsyncSession) -> ListReportsUseCase:
        return ListReportsUseCase(self.repositories(session).reports, self.access_policy(session))

    def get_report(self, session: AsyncSession) -> GetReportUseCase:
        r = self.repositories(session)
        return GetReportUseCase(r.reports, self.access_policy(session), r.uow)

    def delete_report(self, session: AsyncSession) -> DeleteReportUseCase:
        r = self.repositories(session)
        return DeleteReportUseCase(r.reports, self._auditor(r), r.uow, self.access_policy(session))
