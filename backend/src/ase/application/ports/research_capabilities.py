"""Optional, explicit provider contracts independent of bounded collection."""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ase.domain.research import ResearchQuery
from ase.domain.research_plan import UNKNOWN_SPATIAL_SCOPE, UNKNOWN_TEMPORAL_SCOPE


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    language: str | None = None
    query_language_aliases: tuple[str, ...] = ()
    temporal_scope: str = UNKNOWN_TEMPORAL_SCOPE
    spatial_scope: str = UNKNOWN_SPATIAL_SCOPE
    supports_planned_terms: bool = False
    registry_namespaces: tuple[str, ...] = ()


@runtime_checkable
class DescribedResearchProvider(Protocol):
    @property
    def capabilities(self) -> ProviderCapabilities: ...


@runtime_checkable
class AreaResearchProvider(Protocol):
    def supports_area(self, query: ResearchQuery) -> bool: ...


@runtime_checkable
class RegistryResearchProvider(Protocol):
    def registry_subject(self, namespace: str, value: str) -> str | None: ...
