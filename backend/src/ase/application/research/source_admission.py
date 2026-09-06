"""Private provider admission and release checks, without publishing results."""

from ase.application.ports.research import ResearchProvider
from ase.application.ports.source_controls import SourceAdmission
from ase.domain.research import CollectionAttempt, CollectionStatus, ResearchBatch, ResearchQuery


class ControlledResearchProvider:
    def __init__(self, provider: ResearchProvider, admission: SourceAdmission) -> None:
        self._provider, self._admission = provider, admission

    @property
    def id(self) -> str:
        return self._provider.id

    @property
    def name(self) -> str:
        return self._provider.name

    @property
    def language(self) -> str | None:
        value = getattr(self._provider, "language", None)
        return value if isinstance(value, str) else None

    @property
    def query_language_aliases(self) -> tuple[str, ...]:
        values = getattr(self._provider, "query_language_aliases", ())
        return tuple(value for value in values if isinstance(value, str))

    def supports(self, query: ResearchQuery) -> bool:
        return self._provider.supports(query)

    @property
    def temporal_scope(self) -> str:
        fallback = (
            "Bounded available records only; complete historical coverage is not established."
        )
        value = getattr(self._provider, "temporal_scope", fallback)
        return value if isinstance(value, str) else fallback

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
