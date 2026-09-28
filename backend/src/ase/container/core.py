"""Core services the Container builds in __init__, declared once for its mixins.

Every feature mixin inherits ContainerCore so it can be type-checked on its own. The
annotations have no runtime effect: Container.__init__ assigns the attributes and the
mixins define the methods whose signatures appear here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import asyncio
    from collections.abc import Mapping
    from datetime import timedelta

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from ase.adapters.feeds.digitraffic_http import DigitrafficHttpClient
    from ase.adapters.feeds.http import FeedHttpClient
    from ase.adapters.research_records.sec_client import SecClient
    from ase.adapters.research_records.sec_selections import BoundedSecSelections
    from ase.adapters.store.memory import InMemoryEventStore
    from ase.application.access import AccessPolicy
    from ase.application.ai_usage import AiUsageAccounting
    from ase.application.auditing import Auditor
    from ase.application.cameras import CameraCatalogueService
    from ase.application.dto import RateLimits
    from ase.application.feeds.health import HealthRegistry
    from ase.application.feeds.scheduler import FeedScheduler
    from ase.application.ports import (
        AccessTokenIssuer,
        Clock,
        EmailSender,
        PasswordHasher,
        RateLimiter,
    )
    from ase.application.ports.archive import Archiver
    from ase.application.ports.embeddings import EmbeddingGateway
    from ase.application.ports.feeds import EventBus
    from ase.application.ports.geo import CountryDirectory
    from ase.application.ports.llm import LlmGateway, LlmModelDiscovery, SecretCipher
    from ase.application.ports.research import ResearchCollection
    from ase.application.ports.research_inputs import DocumentImportPort, ResearchInputStore
    from ase.application.ports.services import LinkBuilder, TokenGenerator
    from ase.application.ports.source_controls import SourceAdmission
    from ase.application.ports.trackers import ConflictDirectory
    from ase.application.ports.warning import AlertNotifier
    from ase.application.reports.access import GetReportUseCase
    from ase.application.trackers.aviation import WatchedArea
    from ase.container.repositories import Repositories
    from ase.domain.aviation import JamMap
    from ase.domain.grading import SourceProfile
    from ase.domain.reasoning import ReasoningEffortPolicy
    from ase.domain.sources import SourceSpec
    from ase.infrastructure.settings import Settings


class ContainerCore:
    """Attributes and cross-mixin methods shared by the Container's mixins."""

    _dummy_hash: str
    archiver: Archiver
    bus: EventBus
    cameras: CameraCatalogueService
    cipher: SecretCipher
    clock: Clock
    conflicts: ConflictDirectory
    countries: CountryDirectory
    email_sender: EmailSender
    embedding_gateway: EmbeddingGateway
    embedding_lock: asyncio.Lock
    generator: TokenGenerator
    hasher: PasswordHasher
    health: HealthRegistry
    http: FeedHttpClient
    issuer: AccessTokenIssuer
    jam: JamMap
    limiter: RateLimiter
    limits: RateLimits
    links: LinkBuilder
    llm: LlmGateway
    marine_http: DigitrafficHttpClient
    model_discovery: LlmModelDiscovery
    notifier: AlertNotifier
    public_firms_http: FeedHttpClient
    reasoning_effort: ReasoningEffortPolicy
    refresh_ttl: timedelta
    research: ResearchCollection
    research_importer: DocumentImportPort
    research_inputs: ResearchInputStore
    research_sources: tuple[SourceSpec, ...]
    scheduler: FeedScheduler
    sec_client: SecClient
    sec_selections: BoundedSecSelections
    session_factory: async_sessionmaker[AsyncSession]
    settings: Settings
    source_admission: SourceAdmission
    source_profiles: Mapping[str, SourceProfile]
    store: InMemoryEventStore
    watch_areas: tuple[WatchedArea, ...]

    if TYPE_CHECKING:
        # A cached property on AssistantWiring that other mixins read.
        @property
        def ai_usage_accounting(self) -> AiUsageAccounting: ...

        def _auditor(self, repos: Repositories) -> Auditor: ...

        async def _cyber_background(self) -> str: ...

        async def _maritime_background(self) -> str: ...

        def access_policy(self, session: AsyncSession) -> AccessPolicy: ...

        async def aviation_background(self, session: AsyncSession) -> str: ...

        def get_report(self, session: AsyncSession) -> GetReportUseCase: ...

        def public_infrastructure(self) -> dict[str, Any]: ...

        def repositories(self, session: AsyncSession) -> Repositories: ...
