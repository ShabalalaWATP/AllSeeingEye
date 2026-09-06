"""Direction (docs/04 section 7): areas of interest and collection plans.

A collection plan is a named question set: Priority Intelligence Requirements broken into
Specific Intelligence Requirements, each with keywords and categories, scoped to an area
of interest or a set of nations. Events are matched against the plan on demand from the
live store; nothing about the matching is stored.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from ase.domain.direction import Direction
from ase.domain.events import BoundingBox, Category, Event

MAX_PIRS = 8
MAX_SIRS = 12
MAX_KEYWORDS = 20
AREA_KINDS = ("bbox", "countries")


@dataclass(frozen=True, slots=True)
class AreaOfInterest:
    id: UUID
    name: str
    kind: str
    bbox: BoundingBox | None
    countries: tuple[str, ...]
    created_by: UUID
    created_at: datetime
    description: str = ""
    team_id: UUID | None = None

    def contains(self, event: Event) -> bool:
        if self.kind == "bbox":
            return (
                self.bbox is not None
                and event.point is not None
                and self.bbox.contains(event.point)
            )
        return event.country_iso is not None and event.country_iso in self.countries


@dataclass(frozen=True, slots=True)
class Sir:
    code: str
    text: str
    keywords: tuple[str, ...] = ()
    categories: tuple[Category, ...] = ()


@dataclass(frozen=True, slots=True)
class Pir:
    code: str
    text: str
    sirs: tuple[Sir, ...] = ()


@dataclass(frozen=True, slots=True)
class CollectionPlan:
    id: UUID
    name: str
    description: str
    aoi_id: UUID | None
    countries: tuple[str, ...]
    pirs: tuple[Pir, ...]
    enabled: bool
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    team_id: UUID | None = None

    @property
    def sirs(self) -> tuple[Sir, ...]:
        return tuple(sir for pir in self.pirs for sir in pir.sirs)

    def search_terms(self) -> tuple[str, ...]:
        seen: list[str] = []
        for sir in self.sirs:
            for keyword in sir.keywords:
                if keyword.lower() not in [s.lower() for s in seen]:
                    seen.append(keyword)
        return tuple(seen[: MAX_KEYWORDS * 2])

    def direction(self) -> Direction:
        """The plan as the direction a report is written to: no model call needed."""
        categories: list[Category] = []
        for sir in self.sirs:
            for category in sir.categories:
                if category not in categories:
                    categories.append(category)
        return Direction(
            pir=self.pirs[0].text if self.pirs else self.name,
            sirs=tuple(sir.text for sir in self.sirs),
            eeis=(),
            search_terms=self.search_terms(),
            categories=tuple(categories),
        )


def sir_matches(sir: Sir, event: Event) -> bool:
    """A SIR matches when its keywords appear in the text and its categories allow it."""
    if sir.categories and event.category not in sir.categories:
        return False
    if not sir.keywords:
        return bool(sir.categories)
    text = f"{event.title} {event.summary or ''}".lower()
    return any(keyword.lower() in text for keyword in sir.keywords)


def plan_matches(plan: CollectionPlan, event: Event) -> tuple[str, ...]:
    """The codes of the SIRs an event answers; scope is the caller's business."""
    return tuple(sir.code for sir in plan.sirs if sir_matches(sir, event))


def in_scope(plan: CollectionPlan, aoi: AreaOfInterest | None, event: Event) -> bool:
    if aoi is not None and not aoi.contains(event):
        return False
    if plan.countries and aoi is None:
        return event.country_iso is not None and event.country_iso in plan.countries
    return True


def numbered(
    pirs: Sequence[tuple[str, Sequence[tuple[str, Sequence[str], Sequence[Category]]]]],
) -> tuple[Pir, ...]:
    """Assign PIR-n and SIR-n.m codes in order, bounding counts and keyword lists."""
    result: list[Pir] = []
    for p_index, (pir_text, sirs) in enumerate(list(pirs)[:MAX_PIRS], 1):
        numbered_sirs = tuple(
            Sir(
                code=f"SIR-{p_index}.{s_index}",
                text=" ".join(sir_text.split())[:300],
                keywords=tuple(" ".join(k.split())[:60] for k in keywords if k.strip())[
                    :MAX_KEYWORDS
                ],
                categories=tuple(dict.fromkeys(categories)),
            )
            for s_index, (sir_text, keywords, categories) in enumerate(list(sirs)[:MAX_SIRS], 1)
            if sir_text.strip()
        )
        if pir_text.strip():
            result.append(
                Pir(
                    code=f"PIR-{p_index}", text=" ".join(pir_text.split())[:300], sirs=numbered_sirs
                )
            )
    return tuple(result)
