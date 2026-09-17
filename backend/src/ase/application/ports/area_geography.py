"""The only route from a report's scope to packaged geometry, with nothing fetched."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from ase.domain.area_context import AreaGeographyResult
from ase.domain.research_area import ResearchArea


@dataclass(frozen=True, slots=True)
class EvidencePlacement:
    """One selected item's declared position and how well that position is known."""

    label: str
    lon: float | None
    lat: float | None
    geo_confidence: str


@dataclass(frozen=True, slots=True)
class ScopeSample:
    """One instrument record's position, offered to the scope for an exact inside test."""

    key: str
    lon: float
    lat: float


@dataclass(frozen=True, slots=True)
class ScopeRequest:
    """The scope arguments a caller already holds, so a second call cannot disagree."""

    area: ResearchArea | None
    country_isos: tuple[str, ...]
    box: tuple[float, float, float, float] | None = None
    box_label: str | None = None


class AreaGeography(Protocol):
    def assemble(
        self,
        *,
        area: ResearchArea | None,
        country_isos: tuple[str, ...],
        box: tuple[float, float, float, float] | None = None,
        box_label: str | None = None,
        placements: Sequence[EvidencePlacement] = (),
        cameras: bool = False,
    ) -> AreaGeographyResult | None:
        """Resolve the scope and classify placements, or None when nothing resolves."""
        ...

    def locate(
        self,
        *,
        area: ResearchArea | None,
        country_isos: tuple[str, ...],
        box: tuple[float, float, float, float] | None = None,
        box_label: str | None = None,
        samples: Sequence[ScopeSample] = (),
    ) -> frozenset[str]:
        """Keys of the samples inside the resolved scope; empty when nothing resolves."""
        ...
