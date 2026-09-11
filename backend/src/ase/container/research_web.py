"""Shared native-search transport and per-destination runtime policy wiring."""

from functools import cached_property
from typing import TYPE_CHECKING

from ase.adapters.llm.openai_web_search import OpenAiWebSearchGateway
from ase.adapters.persistence.web_search_usage import SqlWebSearchUsage
from ase.application.reports.fresh_web_research import FreshWebResearch

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from ase.application.ports.services import Clock, RateLimiter
    from ase.application.ports.source_controls import SourceAdmission


class WebResearchWiring:
    if TYPE_CHECKING:
        clock: Clock
        limiter: RateLimiter
        source_admission: SourceAdmission
        session_factory: async_sessionmaker[AsyncSession]

    async def close_web_search(self) -> None:
        if "web_search_gateway" in self.__dict__:
            await self.web_search_gateway.aclose()

    @cached_property
    def web_search_gateway(self) -> OpenAiWebSearchGateway:
        return OpenAiWebSearchGateway()

    @cached_property
    def fresh_web_research(self) -> FreshWebResearch:
        return FreshWebResearch(
            self.web_search_gateway,
            self.source_admission,
            self.clock,
            self.limiter,
            SqlWebSearchUsage(self.session_factory).record,
        )
