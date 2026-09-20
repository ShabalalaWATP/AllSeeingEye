"""One compatibility boundary for legacy metadata and shared provider decoration.

New providers expose immutable ``capabilities``. Legacy attributes remain supported
here so adopting that contract does not silently drop existing collection coverage.
Wrappers forward the complete value, including future metadata fields, unchanged.
"""

from ase.application.ports.research import ResearchProvider
from ase.application.ports.research_capabilities import (
    AreaResearchProvider,
    DescribedResearchProvider,
    ProviderCapabilities,
    RegistryResearchProvider,
)
from ase.domain.research import ResearchQuery
from ase.domain.research_plan import UNKNOWN_SPATIAL_SCOPE, UNKNOWN_TEMPORAL_SCOPE


def _strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        return ()
    return tuple(item for item in value if isinstance(item, str))


def _scope(value: object, fallback: str) -> str:
    return value if isinstance(value, str) and value.strip() and len(value) <= 1000 else fallback


def provider_capabilities(provider: ResearchProvider) -> ProviderCapabilities:
    if isinstance(provider, DescribedResearchProvider):
        metadata = provider.capabilities
        if isinstance(metadata, ProviderCapabilities):
            return metadata
    language = getattr(provider, "language", None)
    return ProviderCapabilities(
        language=language if isinstance(language, str) else None,
        query_language_aliases=_strings(getattr(provider, "query_language_aliases", ())),
        temporal_scope=_scope(getattr(provider, "temporal_scope", None), UNKNOWN_TEMPORAL_SCOPE),
        spatial_scope=_scope(getattr(provider, "spatial_scope", None), UNKNOWN_SPATIAL_SCOPE),
        supports_planned_terms=getattr(provider, "supports_planned_terms", False) is True,
        registry_namespaces=_strings(getattr(provider, "registry_namespaces", ())),
    )


class ProviderDecorator:
    """Preserve identity and optional contracts while subclasses own collection policy."""

    def __init__(self, provider: ResearchProvider) -> None:
        self._provider = provider

    @property
    def id(self) -> str:
        return self._provider.id

    @property
    def name(self) -> str:
        return self._provider.name

    @property
    def capabilities(self) -> ProviderCapabilities:
        return provider_capabilities(self._provider)

    def supports(self, query: ResearchQuery) -> bool:
        return self._provider.supports(query)

    def supports_area(self, query: ResearchQuery) -> bool:
        return (
            isinstance(self._provider, AreaResearchProvider)
            and self._provider.supports_area(query) is True
        )

    def registry_subject(self, namespace: str, value: str) -> str | None:
        if not isinstance(self._provider, RegistryResearchProvider) or not callable(
            self._provider.registry_subject
        ):
            return None
        result = self._provider.registry_subject(namespace, value)
        return result if isinstance(result, str) else None
