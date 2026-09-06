"""Administration factories separated from shared runtime construction."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.llm.bedrock import BedrockConverseGateway
from ase.adapters.llm.openai_compatible import OpenAiCompatibleGateway
from ase.adapters.llm.router import RoutingLlmGateway
from ase.adapters.security.cipher import FernetCipher
from ase.application.admin.audit import ListAuditUseCase
from ase.application.admin.llm import (
    CreateLlmProfileUseCase,
    DeleteLlmProfileUseCase,
    ListLlmProfilesUseCase,
    ListLlmUsageUseCase,
    UpdateLlmProfileUseCase,
)
from ase.application.admin.llm_connections import LlmConnectionsUseCase
from ase.application.admin.llm_testing import DiscoverLlmModelsUseCase, TestLlmProfileUseCase
from ase.application.admin.requests import (
    ApproveRequestUseCase,
    ListRequestsUseCase,
    RejectRequestUseCase,
)
from ase.application.admin.users import IssueResetLinkUseCase, ListUsersUseCase, UpdateUserUseCase

if TYPE_CHECKING:
    from ase.application.access import AccessPolicy
    from ase.application.auditing import Auditor
    from ase.application.ports import Clock, EmailSender
    from ase.application.ports.embeddings import EmbeddingGateway
    from ase.application.ports.llm import LlmGateway, LlmModelDiscovery, SecretCipher
    from ase.application.ports.services import LinkBuilder, TokenGenerator
    from ase.container.repositories import Repositories


class AdminWiring:
    if TYPE_CHECKING:
        cipher: SecretCipher
        clock: Clock
        llm: LlmGateway
        model_discovery: LlmModelDiscovery
        embedding_gateway: EmbeddingGateway
        generator: TokenGenerator
        links: LinkBuilder
        email_sender: EmailSender

        def repositories(self, session: AsyncSession) -> Repositories: ...
        def _auditor(self, repos: Repositories) -> Auditor: ...
        def access_policy(self, session: AsyncSession) -> AccessPolicy: ...

    def initialise_models(self, encryption_key: str | None) -> None:
        self.cipher = FernetCipher(encryption_key)
        self._llm_gateway = RoutingLlmGateway(OpenAiCompatibleGateway(), BedrockConverseGateway())
        self.llm = self._llm_gateway
        self.model_discovery = self._llm_gateway

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
        )

    def discover_llm_models(self, session: AsyncSession) -> DiscoverLlmModelsUseCase:
        r = self.repositories(session)
        return DiscoverLlmModelsUseCase(
            r.llm_profiles, self.cipher, self.model_discovery, self.access_policy(session), r.uow
        )
