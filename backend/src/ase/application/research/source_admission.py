"""Private provider admission and release checks, without publishing results."""

from ase.application.ports.research import ResearchProvider
from ase.application.ports.source_controls import SourceAdmission
from ase.application.research.provider_capabilities import ProviderDecorator
from ase.domain.research import CollectionAttempt, CollectionStatus, ResearchBatch, ResearchQuery


class ControlledResearchProvider(ProviderDecorator):
    def __init__(self, provider: ResearchProvider, admission: SourceAdmission) -> None:
        super().__init__(provider)
        self._admission = admission

    def _disabled(self) -> ResearchBatch:
        return ResearchBatch(
            attempts=(
                CollectionAttempt(
                    self.id,
                    self.name,
                    CollectionStatus.UNAVAILABLE,
                    explanation=(
                        "This source is disabled by the administrator. No results were admitted."
                    ),
                ),
            )
        )

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        if not await self._admission.enabled(self.id):
            return self._disabled()
        result = await self._provider.collect(query)
        async with self._admission.guard():
            return result if await self._admission.enabled(self.id) else self._disabled()
