"""Composition for request-local Eye answers and metadata-only usage accounting."""

import asyncio
from functools import cached_property
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.teams import SqlTeamRepository
from ase.application.ai_usage import AiUsageAccounting
from ase.application.ai_usage_gateway import AllowanceLlmGateway
from ase.application.ai_usage_views import AiUsageViews
from ase.application.assistant.alert_context import AlertContextReader
from ase.application.assistant.continuation import AssistantCapacity
from ase.application.assistant.report_context import ReportContextReader
from ase.application.assistant.retrieval import AssistantRetrieval
from ase.application.assistant.service import MapAssistant
from ase.application.model_routing import ModelRouting
from ase.container.core import ContainerCore
from ase.domain.ai_usage import AiAttribution
from ase.domain.llm import LlmUsage

if TYPE_CHECKING:
    from ase.application.ports.llm import LlmGateway


class AssistantWiring(ContainerCore):
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

    def system_llm_gateway(self) -> "LlmGateway":
        """Shared unattended work (feed translation, conflict screening) uses the system budget."""
        return AllowanceLlmGateway(
            self.llm,
            self.ai_usage_accounting,
            attribution=AiAttribution.system_work(),
            profile_id=None,
            purpose_prefix="system",
            strict=False,
        )

    def ai_usage_views(self, session: AsyncSession) -> AiUsageViews:
        repos = self.repositories(session)
        return AiUsageViews(
            repos.ai_usage,
            SqlTeamRepository(session),
            repos.users,
            self.clock,
            ModelRouting(repos.llm_profiles, repos.llm_bindings),
            self.reasoning_effort,
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
            AlertContextReader(
                repos.alerts, self.access_policy(session), self.store, self.source_admission
            ),
        )
