"""Composition for the plain-English economy explainer: facts in, one metered call out."""

from __future__ import annotations

import asyncio
from functools import cached_property
from typing import TYPE_CHECKING, cast

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.economy_explainer import SqlEconomyExplainerRepository
from ase.application.ai_usage_gateway import AllowanceLlmGateway
from ase.application.economy_explainer import EconomyExplainerService
from ase.application.economy_explainer_facts import FactPack, build_fact_pack
from ase.application.economy_explainer_model import ExplainerGenerator
from ase.application.model_routing import ModelRouting
from ase.container.core import ContainerCore
from ase.domain.ai_usage import AiAttribution
from ase.domain.economy_periods import EconomyWindowDays
from ase.domain.llm import LlmUsage

if TYPE_CHECKING:
    from ase.application.ports.llm import LlmGateway
    from ase.container import Container

NEWS_LIMIT = 40
USAGE_TIMEOUT = 2


class EconomyExplainerWiring(ContainerCore):
    @cached_property
    def economy_explainer_admission(self) -> asyncio.Lock:
        """One generation at a time; a second request is told a summary is being written."""
        return asyncio.Lock()

    def economy_explainer_gateway(self) -> LlmGateway:
        return AllowanceLlmGateway(
            self.llm,
            self.ai_usage_accounting,
            attribution=AiAttribution.system_work(),
            profile_id=None,
            # An empty prefix keeps the ledger purpose exactly "economy_explainer".
            purpose_prefix="",
            strict=False,
        )

    async def economy_fact_pack(self) -> FactPack:
        container = cast("Container", self)
        snapshot = await container.economy.snapshot()
        news = await container.economy_news.read("WORLD", NEWS_LIMIT, EconomyWindowDays.TWO)
        # Disabled sources must not reach the model, so filter under the release guard.
        async with container.source_admission.guard():
            visible = await container.economy.refilter(snapshot)
            released = await container.economy_news.refilter(news)
        return build_fact_pack(visible, released.items)

    def economy_explainer(self, session: AsyncSession) -> EconomyExplainerService:
        repos = self.repositories(session)

        async def record_usage(usage: LlmUsage) -> None:
            async with asyncio.timeout(USAGE_TIMEOUT), self.session_factory() as inner:
                inner_repos = self.repositories(inner)
                await inner_repos.llm_usage.add(usage)
                await inner_repos.uow.commit()

        return EconomyExplainerService(
            SqlEconomyExplainerRepository(session),
            repos.uow,
            ModelRouting(repos.llm_profiles, repos.llm_bindings),
            ExplainerGenerator(
                self.economy_explainer_gateway(),
                self.cipher,
                self.clock,
                record_usage,
            ),
            self.economy_fact_pack,
            self.clock,
            self.economy_explainer_admission,
        )
