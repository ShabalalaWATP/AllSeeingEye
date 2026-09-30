"""Composition root: the only package that wires concrete adapters to application ports.

The core here builds the shared services and the auth and admin use cases; the feature
factories (reports, trackers, direction) live in the mixin in features.py.
"""

from __future__ import annotations

import asyncio
import secrets
from collections.abc import Sequence
from datetime import timedelta

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.archive.wayback import NullArchiver, WaybackArchiver
from ase.adapters.bus.memory import InMemoryEventBus
from ase.adapters.feeds.adsb_watch import load_watch_areas
from ase.adapters.feeds.barentswatch_http import BarentsWatchHttpClient
from ase.adapters.feeds.digitraffic_http import DigitrafficHttpClient
from ase.adapters.feeds.host_pacing import DEFAULT_HOST_INTERVALS, HostPacer
from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.feeds.mastodon_watch import watch_host_intervals
from ase.adapters.feeds.satellite_http import SatelliteHttpClient
from ase.adapters.feeds.youtube_channels import channel_host_intervals
from ase.adapters.geo.conflicts import ConflictIndex
from ase.adapters.geo.countries import CountryIndex
from ase.adapters.links import PublicLinkBuilder
from ase.adapters.llm.embeddings import OpenAiEmbeddingGateway
from ase.adapters.notify.webhook import NullNotifier
from ase.adapters.persistence.baselines import SqlBaselineSink
from ase.adapters.persistence.session import create_engine, ensure_sqlite_directory
from ase.adapters.persistence.source_controls import SqlSourceAdmission
from ase.adapters.security.hasher import Argon2PasswordHasher
from ase.adapters.security.jwt_issuer import JwtAccessTokenIssuer
from ase.adapters.security.tokens import SecretsTokenGenerator
from ase.adapters.store.memory import InMemoryEventStore
from ase.adapters.tiles.os_maps import NullTileProvider, OsMapsTileProvider
from ase.adapters.translate.language import LangidDetector, NullDetector
from ase.application.auditing import Auditor
from ase.application.feeds.geo import CountryStage
from ase.application.feeds.grading import GradingService, profiles_from_specs
from ase.application.feeds.health import HealthRegistry
from ase.application.feeds.language import LanguageStage
from ase.application.feeds.pipeline import Normaliser, Pipeline
from ase.application.feeds.scheduler import FeedScheduler
from ase.application.feeds.streams import StreamLimiter
from ase.application.ports import Clock, EmailSender, RateLimiter
from ase.application.ports.archive import Archiver
from ase.application.ports.feeds import FeedConnector
from ase.application.ports.geo import CountryDirectory
from ase.application.ports.language import LanguageDetector
from ase.application.ports.tiles import TileProvider
from ase.application.ports.trackers import ConflictDirectory
from ase.application.ports.warning import AlertNotifier
from ase.application.trackers.aviation import AviationMonitor, WatchedArea
from ase.container.acled import build_acled_tokens
from ase.container.admin import AdminWiring
from ase.container.assistant import AssistantWiring
from ase.container.auth import AuthWiring
from ase.container.conflict_screening import build_conflict_screening
from ase.container.cyber import CyberWiring
from ase.container.economy import EconomyWiring
from ase.container.economy_briefing import EconomyBriefingWiring
from ase.container.economy_explainer import EconomyExplainerWiring
from ase.container.email import build_email_sender
from ase.container.features import FeatureWiring
from ase.container.feed_services import build_feed_connectors, build_research_service
from ase.container.lifecycle import dispose_resources
from ase.container.map_services import MapWiring
from ase.container.private_records import PrivateRecordWiring
from ase.container.public_figures import PublicFigureWiring
from ase.container.reference import ReferenceWiring
from ase.container.repositories import Repositories as Repositories
from ase.container.repositories import build_repositories
from ase.container.research_inputs import ResearchInputWiring
from ase.container.research_usage import ResearchUsageWiring
from ase.container.sec_filings import SecFilingWiring
from ase.container.session_freshness import build_sessions
from ase.container.source_inventory import SourceInventoryWiring
from ase.container.team_board import TeamBoardWiring
from ase.container.ukraine import UkraineWiring
from ase.domain.aviation import JamMap
from ase.infrastructure.clock import SystemClock
from ase.infrastructure.rate_limit import InMemorySlidingWindowLimiter
from ase.infrastructure.settings import Environment, Settings

log = structlog.get_logger(__name__)


class Container(
    ResearchUsageWiring,
    MapWiring,
    PrivateRecordWiring,
    FeatureWiring,
    ResearchInputWiring,
    SecFilingWiring,
    AdminWiring,
    AuthWiring,
    AssistantWiring,
    EconomyWiring,
    EconomyBriefingWiring,
    EconomyExplainerWiring,
    CyberWiring,
    SourceInventoryWiring,
    PublicFigureWiring,
    ReferenceWiring,
    UkraineWiring,
    TeamBoardWiring,
):
    def __init__(
        self,
        settings: Settings,
        *,
        clock: Clock | None = None,
        limiter: RateLimiter | None = None,
        email_sender: EmailSender | None = None,
        connectors: Sequence[FeedConnector] | None = None,
    ) -> None:
        self.settings = settings
        self.clock: Clock = clock or SystemClock()
        self.limiter: RateLimiter = limiter or InMemorySlidingWindowLimiter(self.clock)
        self.email_sender: EmailSender = email_sender or build_email_sender(settings)
        self._initialise_database()
        self._initialise_authentication()
        self._initialise_live_store()
        self._initialise_language()
        self._initialise_http()
        self._initialise_source_services()
        self._initialise_feeds(connectors)
        self._initialise_operational_services()

    def _initialise_database(self) -> None:
        settings = self.settings
        ensure_sqlite_directory(settings.database_url)
        self.engine = create_engine(settings.database_url)
        self.bus, self.health = InMemoryEventBus(), HealthRegistry()
        self.session_signals, self.session_freshness, self.session_factory = build_sessions(
            settings, self.clock, self.bus, self.engine
        )

    def _initialise_authentication(self) -> None:
        settings = self.settings
        self.hasher = Argon2PasswordHasher()
        self.issuer = JwtAccessTokenIssuer(
            settings.jwt_secret_value, timedelta(minutes=settings.access_token_minutes), self.clock
        )
        self.generator = SecretsTokenGenerator()
        self.links = PublicLinkBuilder(settings.public_base_url)
        self.limits = settings.rate_limits
        self.initialise_research_inputs(settings)
        self.initialise_cyber()
        self.refresh_ttl = timedelta(days=settings.refresh_token_days)
        # Verified against on unknown emails so login timing does not reveal existence.
        self._dummy_hash = self.hasher.hash(secrets.token_urlsafe(16))

    def _initialise_live_store(self) -> None:
        settings = self.settings
        # The fusion core: bounded live store, in-process bus, connectors and their scheduler.
        self.store = InMemoryEventStore(
            memory_budget_bytes=settings.live_store_memory_mb * 1024 * 1024
        )
        self.countries: CountryDirectory = CountryIndex.from_resource()
        self.conflicts: ConflictDirectory = ConflictIndex.from_resource()
        self.streams = StreamLimiter(settings.max_streams_per_user)
        self.initialise_models(settings.encryption_key_value, settings.reasoning_effort_policy)
        self.embedding_gateway = OpenAiEmbeddingGateway()
        self._embedding_gateway = self.embedding_gateway
        self.embedding_lock = asyncio.Lock()

    def _initialise_language(self) -> None:
        settings = self.settings
        detector: LanguageDetector = (
            NullDetector() if settings.env is Environment.TEST else LangidDetector()
        )
        self.pipeline = Pipeline(
            [Normaliser(), LanguageStage(detector), CountryStage(self.countries, self.countries)]
        )

    def _initialise_http(self) -> None:
        settings = self.settings
        self.http, self.marine_http, self.satellite_http = (
            FeedHttpClient(
                settings.feeds_user_agent,
                host_pacer=HostPacer(
                    {
                        **DEFAULT_HOST_INTERVALS,
                        **channel_host_intervals(),
                        **watch_host_intervals(),
                    }
                ),
            ),
            DigitrafficHttpClient("TheAllSeeingEye/0.1"),
            SatelliteHttpClient(settings.feeds_user_agent),
        )

    def _initialise_source_services(self) -> None:
        settings = self.settings
        self.initialise_sec_filings()
        self.barentswatch_http, self.acled_tokens = (
            BarentsWatchHttpClient(settings.feeds_user_agent),
            build_acled_tokens(settings, self.session_factory, self.cipher, self.clock),
        )
        self.source_admission = SqlSourceAdmission(
            self.session_factory, tuple(settings.disabled_feed_ids)
        )
        self.initialise_economy()
        self._initialise_map_catalogues()

    def _initialise_feeds(self, connectors: Sequence[FeedConnector] | None) -> None:
        settings = self.settings
        self.research = build_research_service(self)
        self.connectors = build_feed_connectors(self, connectors)
        self.source_profiles = profiles_from_specs(
            [*(c.spec for c in self.connectors), *self.research_sources]
        )
        self.grader = GradingService(self.store, self.source_profiles, self.clock)
        self.scheduler = FeedScheduler(
            self.connectors, self.pipeline, self.store, self.bus, self.health, self.clock,
            grader=self.grader, fetch_concurrency=settings.feed_fetch_concurrency,
            admission=self.source_admission,
        )  # fmt: skip

    def _initialise_operational_services(self) -> None:
        settings = self.settings
        os_key = settings.os_maps_key_value
        self.tiles: TileProvider = (
            OsMapsTileProvider(os_key, limiter=self.limiter)
            if os_key is not None
            else NullTileProvider()
        )
        self.jam = JamMap()
        self.watch_areas = tuple(WatchedArea(area.id, area.name) for area in load_watch_areas())
        self.aviation_monitor = AviationMonitor(
            self.store,
            self.jam,
            SqlBaselineSink(self.session_factory),
            self.clock,
            self.watch_areas,
        )
        # External copies are persisted with the alert and delivered by the outbox worker.
        self.notifier: AlertNotifier = NullNotifier()
        self._initialise_background_jobs()
        self.archiver: Archiver = (
            WaybackArchiver(settings.feeds_user_agent)
            if settings.archive_enabled
            else NullArchiver()
        )

    def _initialise_background_jobs(self) -> None:
        self.evaluator = self.build_evaluator()
        self.schedule_runner = self.build_schedule_runner()
        self.translation_queue = self.build_translation_queue()
        self.conflict_screening = build_conflict_screening(self)
        self.social_monitor = self.build_social_monitor()

    async def dispose(self) -> None:
        await dispose_resources(self)

    def repositories(self, session: AsyncSession) -> Repositories:
        return build_repositories(session)

    def _auditor(self, repos: Repositories) -> Auditor:
        return Auditor(repos.audit, self.clock)
