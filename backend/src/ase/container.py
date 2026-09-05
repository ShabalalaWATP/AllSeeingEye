"""Composition root: the only module that wires concrete adapters to application ports."""

from __future__ import annotations

import secrets
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.bus.memory import InMemoryEventBus
from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.feeds.registry import build_connectors
from ase.adapters.geo.countries import CountryIndex
from ase.adapters.links import PublicLinkBuilder
from ase.adapters.notify.null_email import NullEmailSender
from ase.adapters.persistence.audit import SqlAlchemyUnitOfWork, SqlAuditLogRepository
from ase.adapters.persistence.session import (
    create_engine,
    create_session_factory,
    ensure_sqlite_directory,
)
from ase.adapters.persistence.tokens import SqlPasswordTokenRepository, SqlRefreshTokenRepository
from ase.adapters.persistence.users import SqlAccountRequestRepository, SqlUserRepository
from ase.adapters.security.hasher import Argon2PasswordHasher
from ase.adapters.security.jwt_issuer import JwtAccessTokenIssuer
from ase.adapters.security.tokens import SecretsTokenGenerator
from ase.adapters.store.memory import InMemoryEventStore
from ase.adapters.tiles.os_maps import NullTileProvider, OsMapsTileProvider
from ase.application.admin.audit import ListAuditUseCase
from ase.application.admin.requests import (
    ApproveRequestUseCase,
    ListRequestsUseCase,
    RejectRequestUseCase,
)
from ase.application.admin.users import IssueResetLinkUseCase, ListUsersUseCase, UpdateUserUseCase
from ase.application.auditing import Auditor
from ase.application.auth.account_requests import ForgotPasswordUseCase, RequestAccountUseCase
from ase.application.auth.login import LoginUseCase
from ase.application.auth.refresh import LogoutUseCase, RefreshUseCase
from ase.application.auth.sessions import SessionFactory
from ase.application.auth.set_password import SetPasswordUseCase
from ase.application.feeds.geo import CountryStage
from ase.application.feeds.grading import GradingService, profiles_from_specs
from ase.application.feeds.health import HealthRegistry
from ase.application.feeds.pipeline import Normaliser, Pipeline
from ase.application.feeds.scheduler import FeedScheduler
from ase.application.feeds.streams import StreamLimiter
from ase.application.ports import (
    AccountRequestRepository,
    AuditLogRepository,
    Clock,
    EmailSender,
    PasswordTokenRepository,
    RateLimiter,
    RefreshTokenRepository,
    UnitOfWork,
    UserRepository,
)
from ase.application.ports.feeds import FeedConnector
from ase.application.ports.geo import CountryDirectory
from ase.application.ports.tiles import TileProvider
from ase.infrastructure.clock import SystemClock
from ase.infrastructure.rate_limit import InMemorySlidingWindowLimiter
from ase.infrastructure.settings import Settings


@dataclass(slots=True)
class Repositories:
    users: UserRepository
    requests: AccountRequestRepository
    refresh_tokens: RefreshTokenRepository
    password_tokens: PasswordTokenRepository
    audit: AuditLogRepository
    uow: UnitOfWork


class Container:
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
        self.streams = StreamLimiter(settings.max_streams_per_user)
        self.pipeline = Pipeline([Normaliser(), CountryStage(self.countries)])
        self.http = FeedHttpClient(settings.feeds_user_agent)
        self.connectors: list[FeedConnector] = (
            list(connectors)
            if connectors is not None
            else build_connectors(self.http, self.clock, settings.disabled_feed_ids)
        )
        self.grader = GradingService(
            self.store, profiles_from_specs([c.spec for c in self.connectors]), self.clock
        )
        self.scheduler = FeedScheduler(
            self.connectors, self.pipeline, self.store, self.bus, self.health, self.clock,
            grader=self.grader,
        )  # fmt: skip
        os_key = settings.os_maps_key_value
        self.tiles: TileProvider = (
            OsMapsTileProvider(os_key) if os_key is not None else NullTileProvider()
        )

    async def dispose(self) -> None:
        await self.http.aclose()
        await self.tiles.aclose()
        await self.engine.dispose()

    def repositories(self, session: AsyncSession) -> Repositories:
        return Repositories(
            users=SqlUserRepository(session),
            requests=SqlAccountRequestRepository(session),
            refresh_tokens=SqlRefreshTokenRepository(session),
            password_tokens=SqlPasswordTokenRepository(session),
            audit=SqlAuditLogRepository(session),
            uow=SqlAlchemyUnitOfWork(session),
        )

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
            self._auditor(r), r.uow, self._dummy_hash,
        )  # fmt: skip

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
        return RejectRequestUseCase(r.requests, self.clock, self._auditor(r), r.uow)

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
