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
from ase.adapters.feeds.google_news import GoogleNewsWatchlistConnector
from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.feeds.registry import build_connectors
from ase.adapters.geo.conflicts import ConflictIndex
from ase.adapters.geo.countries import CountryIndex
from ase.adapters.links import PublicLinkBuilder
from ase.adapters.llm.embeddings import OpenAiEmbeddingGateway
from ase.adapters.llm.openai_compatible import OpenAiCompatibleGateway
from ase.adapters.notify.null_email import NullEmailSender
from ase.adapters.notify.webhook import NullNotifier, WebhookNotifier
from ase.adapters.persistence.baselines import SqlBaselineSink
from ase.adapters.persistence.session import (
    create_engine,
    create_session_factory,
    ensure_sqlite_directory,
)
from ase.adapters.persistence.totp import SqlTotpRepository
from ase.adapters.persistence.watchlists import SqlWatchlistPlanStore
from ase.adapters.security.cipher import FernetCipher
from ase.adapters.security.hasher import Argon2PasswordHasher
from ase.adapters.security.jwt_issuer import JwtAccessTokenIssuer
from ase.adapters.security.tokens import SecretsTokenGenerator
from ase.adapters.security.totp import EncryptedTotpProvider
from ase.adapters.store.memory import InMemoryEventStore
from ase.adapters.tiles.os_maps import NullTileProvider, OsMapsTileProvider
from ase.adapters.translate.language import LangidDetector, NullDetector
from ase.application.admin.audit import ListAuditUseCase
from ase.application.admin.llm import (
    CreateLlmProfileUseCase,
    DeleteLlmProfileUseCase,
    ListLlmProfilesUseCase,
    ListLlmUsageUseCase,
    TestLlmProfileUseCase,
    UpdateLlmProfileUseCase,
)
from ase.application.admin.requests import (
    ApproveRequestUseCase,
    ListRequestsUseCase,
    RejectRequestUseCase,
)
from ase.application.admin.users import IssueResetLinkUseCase, ListUsersUseCase, UpdateUserUseCase
from ase.application.auditing import Auditor
from ase.application.auth.account_requests import ForgotPasswordUseCase, RequestAccountUseCase
from ase.application.auth.change_password import ChangePasswordUseCase
from ase.application.auth.login import LoginUseCase
from ase.application.auth.refresh import LogoutUseCase, RefreshUseCase
from ase.application.auth.sessions import SessionFactory
from ase.application.auth.set_password import SetPasswordUseCase
from ase.application.auth.totp import TotpUseCase
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
from ase.application.ports.llm import LlmGateway, SecretCipher
from ase.application.ports.tiles import TileProvider
from ase.application.ports.trackers import ConflictDirectory
from ase.application.ports.warning import AlertNotifier
from ase.application.trackers.aviation import AviationMonitor, WatchedArea
from ase.container.features import FeatureWiring
from ase.container.repositories import Repositories as Repositories
from ase.container.repositories import build_repositories
from ase.container.research import research_service
from ase.container.research_inputs import ResearchInputWiring
from ase.domain.aviation import JamMap
from ase.infrastructure.clock import SystemClock
from ase.infrastructure.rate_limit import InMemorySlidingWindowLimiter
from ase.infrastructure.settings import Environment, Settings

log = structlog.get_logger(__name__)


class Container(FeatureWiring, ResearchInputWiring):
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
        self.email_sender: EmailSender = email_sender or NullEmailSender()
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
        self.refresh_ttl = timedelta(days=settings.refresh_token_days)
        # Verified against on unknown emails so login timing does not reveal existence.
        self._dummy_hash = self.hasher.hash(secrets.token_urlsafe(16))
        # The fusion core: bounded live store, in-process bus, connectors and their scheduler.
        self.store = InMemoryEventStore(
            memory_budget_bytes=settings.live_store_memory_mb * 1024 * 1024
        )
        self.bus = InMemoryEventBus()
        self.health = HealthRegistry()
        self.countries: CountryDirectory = CountryIndex.from_resource()
        self.conflicts: ConflictDirectory = ConflictIndex.from_resource()
        self.streams = StreamLimiter(settings.max_streams_per_user)
        self.cipher: SecretCipher = FernetCipher(settings.encryption_key_value)
        self.llm: LlmGateway = OpenAiCompatibleGateway()
        self._llm_gateway = self.llm
        self.embedding_gateway = OpenAiEmbeddingGateway()
        self._embedding_gateway = self.embedding_gateway
        self.embedding_lock = asyncio.Lock()
        detector: LanguageDetector = (
            NullDetector() if settings.env is Environment.TEST else LangidDetector()
        )
        self.pipeline = Pipeline(
            [Normaliser(), LanguageStage(detector), CountryStage(self.countries, self.countries)]
        )
        self.http = FeedHttpClient(settings.feeds_user_agent)
        self.research = research_service(
            self.http,
            self.clock,
            tuple(settings.disabled_feed_ids),
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
        )
        self.connectors: list[FeedConnector] = (
            list(connectors)
            if connectors is not None
            else build_connectors(self.http, self.clock, settings.disabled_feed_ids)
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
        self.evaluator = self.build_evaluator()
        self.schedule_runner = self.build_schedule_runner()
        self.translation_queue = self.build_translation_queue()
        self.social_monitor = self.build_social_monitor()
        self.archiver: Archiver = (
            WaybackArchiver(settings.feeds_user_agent)
            if settings.archive_enabled
            else NullArchiver()
        )

    async def dispose(self) -> None:
        await self.http.aclose()
        await self._llm_gateway.aclose()
        await self._embedding_gateway.aclose()
        await self.tiles.aclose()
        await self.archiver.aclose()
        await self.engine.dispose()

    def repositories(self, session: AsyncSession) -> Repositories:
        return build_repositories(session)

    def _auditor(self, repos: Repositories) -> Auditor:
        return Auditor(repos.audit, self.clock)

    def _sessions(self, repos: Repositories) -> SessionFactory:
        return SessionFactory(
            repos.refresh_tokens, self.issuer, self.generator, self.clock, self.refresh_ttl
        )

    def login(self, session: AsyncSession) -> LoginUseCase:
        r = self.repositories(session)
        return LoginUseCase(
            r.users, self.hasher, self._sessions(r), self.clock, self.limiter, self.limits,
            self._auditor(r), r.uow, self._dummy_hash, totp=self.totp(session),
        )  # fmt: skip

    def totp(self, session: AsyncSession) -> TotpUseCase:
        r = self.repositories(session)
        return TotpUseCase(
            SqlTotpRepository(session),
            EncryptedTotpProvider(self.cipher),
            self.hasher,
            r.refresh_tokens,
            self.clock,
            self.limiter,
            self._auditor(r),
            r.uow,
            r.users,
        )

    def refresh(self, session: AsyncSession) -> RefreshUseCase:
        r = self.repositories(session)
        return RefreshUseCase(
            r.users, r.refresh_tokens, self.generator, self._sessions(r), self.clock,
            self._auditor(r), r.uow,
        )  # fmt: skip

    def logout(self, session: AsyncSession) -> LogoutUseCase:
        r = self.repositories(session)
        return LogoutUseCase(r.refresh_tokens, self.generator, self.clock, self._auditor(r), r.uow)

    def request_account(self, session: AsyncSession) -> RequestAccountUseCase:
        r = self.repositories(session)
        return RequestAccountUseCase(
            r.users, r.requests, self.clock, self.limiter, self.limits, self._auditor(r), r.uow
        )

    def forgot_password(self, session: AsyncSession) -> ForgotPasswordUseCase:
        r = self.repositories(session)
        return ForgotPasswordUseCase(
            r.users, r.password_tokens, self.generator, self.links, self.email_sender, self.clock,
            self.limiter, self.limits, self._auditor(r), r.uow,
        )  # fmt: skip

    def set_password(self, session: AsyncSession) -> SetPasswordUseCase:
        r = self.repositories(session)
        return SetPasswordUseCase(
            r.users, r.password_tokens, r.refresh_tokens, self.hasher, self.generator, self.clock,
            self.limiter, self.limits, self._auditor(r), r.uow,
        )  # fmt: skip

    def change_password(self, session: AsyncSession) -> ChangePasswordUseCase:
        r = self.repositories(session)
        return ChangePasswordUseCase(
            r.users, r.password_tokens, r.refresh_tokens, self.hasher, self.totp(session),
            self.clock, self.limiter, self._auditor(r), r.uow,
        )  # fmt: skip

    def list_requests(self, session: AsyncSession) -> ListRequestsUseCase:
        return ListRequestsUseCase(self.repositories(session).requests)

    def approve_request(self, session: AsyncSession) -> ApproveRequestUseCase:
        r = self.repositories(session)
        return ApproveRequestUseCase(
            r.users, r.requests, r.password_tokens, self.generator, self.links, self.email_sender,
            self.clock, self._auditor(r), r.uow,
        )  # fmt: skip

    def reject_request(self, session: AsyncSession) -> RejectRequestUseCase:
        r = self.repositories(session)
        return RejectRequestUseCase(r.requests, self.clock, self._auditor(r), r.uow, r.users)

    def list_users(self, session: AsyncSession) -> ListUsersUseCase:
        return ListUsersUseCase(self.repositories(session).users)

    def update_user(self, session: AsyncSession) -> UpdateUserUseCase:
        r = self.repositories(session)
        return UpdateUserUseCase(
            r.users, r.refresh_tokens, r.password_tokens, self.clock, self._auditor(r), r.uow
        )

    def issue_reset_link(self, session: AsyncSession) -> IssueResetLinkUseCase:
        r = self.repositories(session)
        return IssueResetLinkUseCase(
            r.users, r.password_tokens, self.generator, self.links, self.clock,
            self._auditor(r), r.uow,
        )  # fmt: skip

    def list_audit(self, session: AsyncSession) -> ListAuditUseCase:
        return ListAuditUseCase(self.repositories(session).audit)

    def list_llm_profiles(self, session: AsyncSession) -> ListLlmProfilesUseCase:
        return ListLlmProfilesUseCase(self.repositories(session).llm_profiles)

    def create_llm_profile(self, session: AsyncSession) -> CreateLlmProfileUseCase:
        r = self.repositories(session)
        return CreateLlmProfileUseCase(
            r.llm_profiles, self.cipher, self.clock, self._auditor(r), r.uow
        )

    def update_llm_profile(self, session: AsyncSession) -> UpdateLlmProfileUseCase:
        r = self.repositories(session)
        return UpdateLlmProfileUseCase(
            r.llm_profiles, self.cipher, self.clock, self._auditor(r), r.uow
        )

    def delete_llm_profile(self, session: AsyncSession) -> DeleteLlmProfileUseCase:
        r = self.repositories(session)
        return DeleteLlmProfileUseCase(r.llm_profiles, self._auditor(r), r.uow)

    def test_llm_profile(self, session: AsyncSession) -> TestLlmProfileUseCase:
        r = self.repositories(session)
        return TestLlmProfileUseCase(
            r.llm_profiles, r.llm_usage, self.cipher, self.llm, self.clock,
            self._auditor(r), r.uow,
            embeddings=self.embedding_gateway,
        )  # fmt: skip

    def list_llm_usage(self, session: AsyncSession) -> ListLlmUsageUseCase:
        return ListLlmUsageUseCase(self.repositories(session).llm_usage)
