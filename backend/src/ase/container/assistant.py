"""Composition for request-local Eye answers and metadata-only usage accounting."""

import asyncio
from functools import cached_property
from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import AsyncSession

from ase.application.ai_usage import AiUsageAccounting
from ase.application.assistant.continuation import AssistantCapacity
from ase.application.assistant.report_context import ReportContextReader
from ase.application.assistant.retrieval import AssistantRetrieval
from ase.application.assistant.service import MapAssistant
from ase.application.model_routing import ModelRouting
from ase.domain.llm import LlmUsage

if TYPE_CHECKING:
    from collections.abc import Mapping

    from sqlalchemy.ext.asyncio import async_sessionmaker

    from ase.adapters.store.memory import InMemoryEventStore
    from ase.application.access import AccessPolicy
    from ase.application.cameras import CameraCatalogueService
    from ase.application.ports import Clock, RateLimiter
    from ase.application.ports.llm import LlmGateway, SecretCipher
    from ase.application.ports.source_controls import SourceAdmission
    from ase.application.reports.access import GetReportUseCase
    from ase.container.repositories import Repositories
    from ase.domain.grading import SourceProfile


class AssistantWiring:
    if TYPE_CHECKING:
        store: InMemoryEventStore
        cameras: CameraCatalogueService
        source_admission: SourceAdmission
        source_profiles: Mapping[str, SourceProfile]
        clock: Clock
        limiter: RateLimiter
        cipher: SecretCipher
        llm: LlmGateway
        session_factory: async_sessionmaker[AsyncSession]

        def repositories(self, session: AsyncSession) -> Repositories: ...
        def get_report(self, session: AsyncSession) -> GetReportUseCase: ...
        def access_policy(self, session: AsyncSession) -> AccessPolicy: ...
        def public_infrastructure(self) -> dict[str, Any]: ...

    @cached_property
    def assistant_capacity(self) -> AssistantCapacity:
        return AssistantCapacity()

    @cached_property
    def ai_usage_accounting(self) -> AiUsageAccounting:
        return AiUsageAccounting(
            self.session_factory,
            lambda session: self.repositories(session).ai_usage,
            self.clock,
        )

    def map_assistant(self, session: AsyncSession) -> MapAssistant:
        repos = self.repositories(session)

        async def record_usage(usage: LlmUsage) -> None:
            async with asyncio.timeout(2), self.session_factory() as usage_session:
                usage_repos = self.repositories(usage_session)
                await usage_repos.llm_usage.add(usage)
                await usage_repos.uow.commit()

        return MapAssistant(
            self.access_policy(session),
            ModelRouting(repos.llm_profiles, repos.llm_bindings),
            AssistantRetrieval(
                self.store,
                self.source_admission,
                self.cameras,
                self.public_infrastructure,
                self.source_profiles,
            ),
            self.source_admission,
            self.llm,
            self.cipher,
            self.clock,
            self.limiter,
            repos.uow,
            self.assistant_capacity,
            record_usage,
            self.ai_usage_accounting,
            ReportContextReader(self.get_report(session)),
        )
