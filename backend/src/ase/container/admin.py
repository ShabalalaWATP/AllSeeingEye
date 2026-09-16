"""Administration factories separated from shared runtime construction."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.feeds.firms_runtime import FirmsConnectionProbe
from ase.adapters.feeds.firms_sensors import FIRMS_SENSORS
from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.llm.bedrock import BedrockConverseGateway
from ase.adapters.llm.effort import MechanicalEffortGateway
from ase.adapters.llm.openai_compatible import OpenAiCompatibleGateway
from ase.adapters.llm.router import RoutingLlmGateway
from ase.adapters.persistence.firms_credentials import SqlFirmsCredentials
from ase.adapters.persistence.source_controls import SqlSourceControlRepository
from ase.adapters.persistence.teams import SqlTeamRepository
from ase.adapters.security.cipher import FernetCipher
from ase.application.admin.audit import ListAuditUseCase
from ase.application.admin.firms_credentials import AdminFirmsCredentials
from ase.application.admin.llm import (
    CreateLlmProfileUseCase,
    DeleteLlmProfileUseCase,
    ListLlmProfilesUseCase,
    ListLlmUsageUseCase,
    UpdateLlmProfileUseCase,
)
from ase.application.admin.llm_connections import LlmConnectionsUseCase
from ase.application.admin.llm_discovery import DiscoverDraftModels
from ase.application.admin.llm_testing import DiscoverLlmModelsUseCase, TestLlmProfileUseCase
from ase.application.admin.requests import (
    ApproveRequestUseCase,
    ListRequestsUseCase,
    RejectRequestUseCase,
)
from ase.application.admin.source_controls import AdminSourceControls
from ase.application.admin.users import IssueResetLinkUseCase, ListUsersUseCase, UpdateUserUseCase
from ase.domain.reasoning import ReasoningEffortPolicy

if TYPE_CHECKING:
    from ase.application.access import AccessPolicy
    from ase.application.ai_usage import AiUsageAccounting
    from ase.application.auditing import Auditor
    from ase.application.feeds.health import HealthRegistry
    from ase.application.feeds.scheduler import FeedScheduler
    from ase.application.ports import Clock, EmailSender
    from ase.application.ports.embeddings import EmbeddingGateway
    from ase.application.ports.llm import LlmGateway, LlmModelDiscovery, SecretCipher
    from ase.application.ports.services import LinkBuilder, RateLimiter, TokenGenerator
    from ase.application.ports.source_controls import SourceAdmission
    from ase.container.repositories import Repositories
    from ase.domain.sources import SourceSpec
    from ase.infrastructure.settings import Settings


class AdminWiring:
    if TYPE_CHECKING:
        http: FeedHttpClient
        public_firms_http: FeedHttpClient
        cipher: SecretCipher
        clock: Clock
        llm: LlmGateway
        model_discovery: LlmModelDiscovery
        embedding_gateway: EmbeddingGateway
        ai_usage_accounting: AiUsageAccounting
        generator: TokenGenerator
        links: LinkBuilder
        email_sender: EmailSender
        limiter: RateLimiter
        source_admission: SourceAdmission
        scheduler: FeedScheduler
        health: HealthRegistry
        research_sources: tuple[SourceSpec, ...]
        settings: Settings

        def repositories(self, session: AsyncSession) -> Repositories: ...
        def _auditor(self, repos: Repositories) -> Auditor: ...
        def access_policy(self, session: AsyncSession) -> AccessPolicy: ...

    def initialise_models(
        self, encryption_key: str | None, effort: ReasoningEffortPolicy | None = None
    ) -> None:
        self.cipher = FernetCipher(encryption_key)
        self._llm_gateway = RoutingLlmGateway(OpenAiCompatibleGateway(), BedrockConverseGateway())
        # Every provider call passes through here, so mechanical purposes are capped once.
        self.reasoning_effort = effort if effort is not None else ReasoningEffortPolicy()
        self.llm = MechanicalEffortGateway(self._llm_gateway, self.reasoning_effort)
        self.model_discovery = self._llm_gateway

    def _resume_firms(self) -> None:
        for sensor in FIRMS_SENSORS:
            self.scheduler.resume(f"firms_viirs_{sensor.suffix}")

    def admin_firms_credentials(self, session: AsyncSession) -> AdminFirmsCredentials:
        r = self.repositories(session)
        return AdminFirmsCredentials(
            r.users,
            r.refresh_tokens,
            SqlFirmsCredentials(session),
            self.cipher,
            FirmsConnectionProbe(self.public_firms_http, self.clock),
            self.clock,
            self.limiter,
            self._auditor(r),
            r.uow,
            self._resume_firms,
            area=self.settings.firms_area,
            environment_managed=bool(self.settings.firms_map_key),
            environment_disabled="firms_viirs_noaa20" in self.settings.disabled_feed_ids,
        )

    def list_requests(self, session: AsyncSession) -> ListRequestsUseCase:
        return ListRequestsUseCase(self.repositories(session).requests)

    def admin_source_controls(self, session: AsyncSession) -> AdminSourceControls:
        r = self.repositories(session)
        return AdminSourceControls(
            r.users,
            r.refresh_tokens,
            SqlSourceControlRepository(session),
            self.source_admission,
            self.scheduler.connectors,
            self.research_sources,
            self.health,
            self.scheduler.resume,
            self.clock,
            self.limiter,
            self._auditor(r),
            r.uow,
            tuple(self.settings.disabled_feed_ids),
        )

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
            r.users, r.refresh_tokens, r.password_tokens, self.clock, self._auditor(r), r.uow,
            SqlTeamRepository(session),
        )  # fmt: skip

    def issue_reset_link(self, session: AsyncSession) -> IssueResetLinkUseCase:
        r = self.repositories(session)
        return IssueResetLinkUseCase(
            r.users, r.password_tokens, self.generator, self.links, self.clock,
            self._auditor(r), r.uow,
        )  # fmt: skip

    def list_audit(self, session: AsyncSession) -> ListAuditUseCase:
        return ListAuditUseCase(self.repositories(session).audit)

    def list_llm_profiles(self, session: AsyncSession) -> ListLlmProfilesUseCase:
        return ListLlmProfilesUseCase(
            self.repositories(session).llm_profiles, self.access_policy(session)
        )

    def create_llm_profile(self, session: AsyncSession) -> CreateLlmProfileUseCase:
        r = self.repositories(session)
        return CreateLlmProfileUseCase(
            r.llm_profiles,
            self.cipher,
            self.clock,
            self._auditor(r),
            r.uow,
            self.access_policy(session),
            r.llm_bindings,
        )

    def update_llm_profile(self, session: AsyncSession) -> UpdateLlmProfileUseCase:
        r = self.repositories(session)
        return UpdateLlmProfileUseCase(
            r.llm_profiles,
            self.cipher,
            self.clock,
            self._auditor(r),
            r.uow,
            self.access_policy(session),
            r.llm_bindings,
        )

    def delete_llm_profile(self, session: AsyncSession) -> DeleteLlmProfileUseCase:
        r = self.repositories(session)
        return DeleteLlmProfileUseCase(
            r.llm_profiles, self._auditor(r), r.uow, self.access_policy(session), r.llm_bindings
        )

    def test_llm_profile(self, session: AsyncSession) -> TestLlmProfileUseCase:
        r = self.repositories(session)
        return TestLlmProfileUseCase(
            r.llm_profiles, r.llm_usage, self.cipher, self.llm, self.clock,
            self._auditor(r), r.uow,
            embeddings=self.embedding_gateway, access=self.access_policy(session),
            ai_usage=self.ai_usage_accounting,
        )  # fmt: skip

    def list_llm_usage(self, session: AsyncSession) -> ListLlmUsageUseCase:
        return ListLlmUsageUseCase(
            self.repositories(session).llm_usage, self.access_policy(session)
        )

    def llm_connections(self, session: AsyncSession) -> LlmConnectionsUseCase:
        r = self.repositories(session)
        return LlmConnectionsUseCase(
            r.llm_profiles,
            r.llm_bindings,
            self.access_policy(session),
            self.clock,
            self._auditor(r),
            r.uow,
            users=r.users,
        )

    def discover_llm_models(self, session: AsyncSession) -> DiscoverLlmModelsUseCase:
        r = self.repositories(session)
        return DiscoverLlmModelsUseCase(
            r.llm_profiles, self.cipher, self.model_discovery, self.access_policy(session), r.uow
        )

    def discover_draft_models(self, session: AsyncSession) -> DiscoverDraftModels:
        r = self.repositories(session)
        return DiscoverDraftModels(
            r.users,
            r.refresh_tokens,
            r.llm_profiles,
            self.cipher,
            self.model_discovery,
            self.clock,
            r.uow,
        )
