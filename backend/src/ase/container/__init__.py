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
from ase.adapters.feeds.adsb_viewport import AircraftInterestQueue
from ase.adapters.feeds.adsb_watch import load_watch_areas
from ase.adapters.feeds.barentswatch_http import BarentsWatchHttpClient
from ase.adapters.feeds.digitraffic_http import DigitrafficHttpClient
from ase.adapters.feeds.firms_runtime import ManagedFirmsConnector
from ase.adapters.feeds.firms_sensors import FIRMS_SENSORS
from ase.adapters.feeds.google_news import GoogleNewsWatchlistConnector
from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.feeds.registry import build_connectors
from ase.adapters.feeds.satellite_http import SatelliteHttpClient
from ase.adapters.geo.camera_http import CameraHttpClient
from ase.adapters.geo.camera_registry import build_sources as build_camera_sources
from ase.adapters.geo.conflicts import ConflictIndex
from ase.adapters.geo.countries import CountryIndex
from ase.adapters.links import PublicLinkBuilder
from ase.adapters.llm.embeddings import OpenAiEmbeddingGateway
from ase.adapters.notify.webhook import NullNotifier, WebhookNotifier
from ase.adapters.persistence.baselines import SqlBaselineSink
from ase.adapters.persistence.session import (
    create_engine,
    create_session_factory,
    ensure_sqlite_directory,
)
from ase.adapters.persistence.source_controls import SqlSourceAdmission
from ase.adapters.persistence.watchlists import SqlWatchlistPlanStore
from ase.adapters.research_records.copernicus import CopernicusFootprintProvider
from ase.adapters.routing.groundwave import NtiaGroundwaveSolver
from ase.adapters.routing.photon import PhotonPlaceSearchGateway
from ase.adapters.routing.terrarium import TERRAIN_TILE_BYTES, TerrariumGateway
from ase.adapters.routing.valhalla import ValhallaRoutingGateway
from ase.adapters.security.hasher import Argon2PasswordHasher
from ase.adapters.security.jwt_issuer import JwtAccessTokenIssuer
from ase.adapters.security.tokens import SecretsTokenGenerator
from ase.adapters.store.memory import InMemoryEventStore
from ase.adapters.tiles.os_maps import NullTileProvider, OsMapsTileProvider
from ase.adapters.translate.language import LangidDetector, NullDetector
from ase.application.auditing import Auditor
from ase.application.auth.sessions import SessionFactory
from ase.application.cameras import CameraCatalogueService
from ase.application.feeds.geo import CountryStage
from ase.application.feeds.grading import GradingService, profiles_from_specs
from ase.application.feeds.health import HealthRegistry
from ase.application.feeds.language import LanguageStage
from ase.application.feeds.map_interests import MapCollectionInterests
from ase.application.feeds.pipeline import Normaliser, Pipeline
from ase.application.feeds.scheduler import FeedScheduler
from ase.application.feeds.streams import StreamLimiter
from ase.application.footprints import FootprintSearchUseCase
from ase.application.groundwave import GroundwaveStudy
from ase.application.navigation import RoutePlanner
from ase.application.place_search import PlaceSearch
from ase.application.ports import Clock, EmailSender, RateLimiter
from ase.application.ports.archive import Archiver
from ase.application.ports.feeds import FeedConnector
from ase.application.ports.geo import CountryDirectory
from ase.application.ports.language import LanguageDetector
from ase.application.ports.tiles import TileProvider
from ase.application.ports.trackers import ConflictDirectory
from ase.application.ports.warning import AlertNotifier
from ase.application.terrain import TerrainSampler
from ase.application.trackers.aviation import AviationMonitor, WatchedArea
from ase.container.admin import AdminWiring
from ase.container.assistant import AssistantWiring
from ase.container.auth import AuthWiring
from ase.container.conflict_screening import build_conflict_screening
from ase.container.cyber import CyberWiring
from ase.container.economy import EconomyWiring
from ase.container.economy_briefing import EconomyBriefingWiring
from ase.container.email import build_email_sender
from ase.container.features import FeatureWiring
from ase.container.lifecycle import dispose_resources
from ase.container.repositories import Repositories as Repositories
from ase.container.repositories import build_repositories
from ase.container.research import research_service
from ase.container.research_inputs import ResearchInputWiring
from ase.container.sec_filings import SecFilingWiring
from ase.domain.aviation import JamMap
from ase.infrastructure.clock import SystemClock
from ase.infrastructure.rate_limit import InMemorySlidingWindowLimiter
from ase.infrastructure.settings import Environment, Settings

log = structlog.get_logger(__name__)


class Container(
    FeatureWiring,
    ResearchInputWiring,
    SecFilingWiring,
    AdminWiring,
    AuthWiring,
    AssistantWiring,
    EconomyWiring,
    EconomyBriefingWiring,
    CyberWiring,
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
        ensure_sqlite_directory(settings.database_url)
        self.engine = create_engine(settings.database_url)
        self.session_factory = create_session_factory(self.engine)
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
        # The fusion core: bounded live store, in-process bus, connectors and their scheduler.
        self.store = InMemoryEventStore(
            memory_budget_bytes=settings.live_store_memory_mb * 1024 * 1024
        )
        self.bus, self.health = InMemoryEventBus(), HealthRegistry()
        self.countries: CountryDirectory = CountryIndex.from_resource()
        self.conflicts: ConflictDirectory = ConflictIndex.from_resource()
        self.streams = StreamLimiter(settings.max_streams_per_user)
        self.initialise_models(settings.encryption_key_value)
        self.embedding_gateway = OpenAiEmbeddingGateway()
        self._embedding_gateway = self.embedding_gateway
        self.embedding_lock = asyncio.Lock()
        detector: LanguageDetector = (
            NullDetector() if settings.env is Environment.TEST else LangidDetector()
        )
        self.pipeline = Pipeline(
            [Normaliser(), LanguageStage(detector), CountryStage(self.countries, self.countries)]
        )
        self.http, self.marine_http, self.satellite_http = (
            FeedHttpClient(settings.feeds_user_agent),
            DigitrafficHttpClient("TheAllSeeingEye/0.1"),
            SatelliteHttpClient(settings.feeds_user_agent),
        )
        self.initialise_sec_filings()
        self.barentswatch_http = BarentsWatchHttpClient(settings.feeds_user_agent)
        self.source_admission = SqlSourceAdmission(
            self.session_factory, tuple(settings.disabled_feed_ids)
        )
        self.initialise_economy()
        self._initialise_map_catalogues()
        self.research = research_service(
            self.http,
            self.clock,
            tuple(settings.disabled_feed_ids),
            admission=self.source_admission,
            retained_store=self.store,
            sec_client=self.sec_client,
            ooni_noncommercial_use_acknowledged=settings.ooni_noncommercial_use_acknowledged,
            uksl_snapshot_path=settings.uksl_snapshot_path,
            ofac_sdn_snapshot_path=settings.ofac_sdn_snapshot_path,
            aiddata_catalogue_path=settings.aiddata_catalogue_path,
            countries=self.countries,
            companies_house_key=(
                settings.companies_house_key.get_secret_value()
                if settings.companies_house_key
                else None
            ),
            certificate_transparency_key=(
                settings.certificate_transparency_key.get_secret_value()
                if settings.certificate_transparency_key
                else None
            ),
            openalex_api_key=(
                settings.openalex_api_key.get_secret_value() if settings.openalex_api_key else None
            ),
            openaq_api_key=(
                settings.openaq_api_key.get_secret_value() if settings.openaq_api_key else None
            ),
        )
        self.connectors: list[FeedConnector] = (
            list(connectors)
            if connectors is not None
            else [
                *build_connectors(
                    self.http,
                    self.clock,
                    settings.disabled_feed_ids,
                    digitraffic_http=self.marine_http,
                    barentswatch_http=self.barentswatch_http,
                    barentswatch_client_id=settings.barentswatch_client_id,
                    barentswatch_client_secret=settings.barentswatch_client_secret,
                    aircraft_interests=self.aircraft_interests,
                    public_firms_http=self.public_firms_http,
                    satellite_http=self.satellite_http,
                    satellite_cache_dir=(
                        settings.satellite_cache_dir
                        if settings.env is not Environment.TEST
                        else None
                    ),
                    include_public_firms=not bool(settings.firms_map_key),
                    ucdp_candidate_version=settings.ucdp_candidate_version,
                    ucdp_access_token=(
                        settings.ucdp_access_token.get_secret_value()
                        if settings.ucdp_access_token
                        else None
                    ),
                    acled_access_token=(
                        settings.acled_access_token.get_secret_value()
                        if settings.acled_access_token
                        else None
                    ),
                    reliefweb_appname=settings.reliefweb_appname,
                    iso3_to_iso2={
                        country.iso3: country.iso2 for country in self.countries.countries()
                    },
                    aisstream_key=settings.aisstream_api_key.get_secret_value()
                    if settings.aisstream_api_key
                    else None,
                ),
                *[
                    ManagedFirmsConnector(
                        self.session_factory,
                        self.public_firms_http,
                        self.clock,
                        self.cipher,
                        environment_key=settings.firms_map_key.get_secret_value()
                        if settings.firms_map_key
                        else None,
                        area=settings.firms_area,
                        disabled="firms_viirs_noaa20" in settings.disabled_feed_ids
                        or f"firms_viirs_{sensor.suffix}" in settings.disabled_feed_ids,
                        sensor=sensor,
                    )
                    for sensor in FIRMS_SENSORS
                ],
            ]
        )
        watchlists = GoogleNewsWatchlistConnector(
            self.http, self.clock, SqlWatchlistPlanStore(self.session_factory)
        )
        if connectors is None and watchlists.spec.id not in settings.disabled_feed_ids:
            self.connectors.append(watchlists)
        self.source_profiles = profiles_from_specs(
            [*(c.spec for c in self.connectors), *self.research_sources]
        )
        self.grader = GradingService(self.store, self.source_profiles, self.clock)
        self.scheduler = FeedScheduler(
            self.connectors, self.pipeline, self.store, self.bus, self.health, self.clock,
            grader=self.grader,
            admission=self.source_admission,
        )  # fmt: skip
        os_key = settings.os_maps_key_value
        self.tiles: TileProvider = (
            OsMapsTileProvider(os_key) if os_key is not None else NullTileProvider()
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
        webhook = settings.alert_webhook_url
        self.notifier: AlertNotifier = (
            WebhookNotifier(webhook, settings.feeds_user_agent) if webhook else NullNotifier()
        )
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

    def _initialise_map_catalogues(self) -> None:
        self.groundwave_study = GroundwaveStudy(NtiaGroundwaveSolver(), self.limiter)
        self.aircraft_interests = AircraftInterestQueue(self.clock)
        self.map_interests = MapCollectionInterests(self.aircraft_interests, self.limiter)
        self.routing_http = FeedHttpClient(self.http.user_agent, max_bytes=2 * 1024 * 1024)
        self.route_planner = RoutePlanner(ValhallaRoutingGateway(self.routing_http), self.limiter)
        self.place_search = PlaceSearch(PhotonPlaceSearchGateway(self.routing_http), self.limiter)
        self.terrain_http = FeedHttpClient(
            self.http.user_agent, max_bytes=TERRAIN_TILE_BYTES, timeout_seconds=10
        )
        self.terrain_gateway = TerrariumGateway(self.terrain_http)
        self.terrain_sampler = TerrainSampler(self.terrain_gateway, self.limiter)
        self.public_firms_http = FeedHttpClient(self.http.user_agent, max_bytes=16 * 1024 * 1024)
        self.camera_http = CameraHttpClient(self.http.user_agent, max_bytes=10 * 1024 * 1024)
        self.cameras = CameraCatalogueService(
            build_camera_sources(
                self.camera_http,
                self.marine_http,
                wsdot_access_code=(
                    self.settings.wsdot_access_code.get_secret_value()
                    if self.settings.wsdot_access_code
                    else None
                ),
            ),
            self.clock,
        )
        self.footprints = FootprintSearchUseCase(
            CopernicusFootprintProvider(self.http, self.clock),
            self.limiter,
            self.clock,
            admission=self.source_admission,
        )

    async def dispose(self) -> None:
        await dispose_resources(self)

    def repositories(self, session: AsyncSession) -> Repositories:
        return build_repositories(session)

    def _auditor(self, repos: Repositories) -> Auditor:
        return Auditor(repos.audit, self.clock)

    def _sessions(self, repos: Repositories) -> SessionFactory:
        return SessionFactory(
            repos.refresh_tokens, self.issuer, self.generator, self.clock, self.refresh_ttl
        )
