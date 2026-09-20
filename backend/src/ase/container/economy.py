"""Shared public economics cache and guarded outbound client lifetime."""

from datetime import timedelta
from typing import TYPE_CHECKING

from ase.adapters.economy.gateway import PublicEconomyGateway
from ase.adapters.feeds.http import FeedHttpClient
from ase.application.economy import EconomyService
from ase.domain.economy_catalogue import ECB_SOURCE
from ase.domain.events import Category, Reliability
from ase.domain.sources import SourceKind, SourceSpec

if TYPE_CHECKING:
    from ase.application.ports.services import Clock
    from ase.application.ports.source_controls import SourceAdmission

ECB_SPEC = SourceSpec(
    id="economic-ecb",
    name="ECB currency reference rates",
    organisation="European Central Bank",
    category=Category.ECONOMIC,
    kind=SourceKind.API,
    url="",
    reliability=Reliability.F,
    poll_interval=timedelta(hours=1),
    homepage=ECB_SOURCE,
    licence_note="ECB working-day reference rates for information, not transaction purposes. "
    "Source attribution required. No RUB rate since suspension; no IRR series.",
)


class EconomyWiring:
    if TYPE_CHECKING:
        http: FeedHttpClient
        clock: Clock
        source_admission: SourceAdmission
        research_sources: tuple[SourceSpec, ...]

    def initialise_economy(self) -> None:
        self.economy_http = FeedHttpClient(
            self.http.user_agent,
            max_bytes=512 * 1024,
            timeout_seconds=15,
        )
        self.economy = EconomyService(
            PublicEconomyGateway(self.economy_http, self.clock),
            self.clock,
            admission=self.source_admission,
        )
        self.research_sources = (*self.research_sources, ECB_SPEC)

    async def close_economy(self) -> None:
        try:
            await self.economy.aclose()
        finally:
            await self.economy_http.aclose()
