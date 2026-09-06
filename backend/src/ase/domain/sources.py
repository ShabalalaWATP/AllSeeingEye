"""Source registry entries: what a feed is, how often it is polled and how reliable it is."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum

from ase.domain.events import Category, Reliability
from ase.domain.source_ratings import SourceRating, source_rating_for


class SourceKind(StrEnum):
    API = "api"
    RSS = "rss"
    GEOJSON = "geojson"
    WEBSOCKET = "websocket"


@dataclass(frozen=True, slots=True)
class SourceSpec:
    id: str
    name: str
    organisation: str
    category: Category
    kind: SourceKind
    url: str
    reliability: Reliability
    poll_interval: timedelta
    parent_organisation: str | None = None
    language: str = "en"
    licence_note: str = ""
    homepage: str = ""
    requires_key: bool = False
    instrument: bool = False
    flags: frozenset[str] = frozenset()
    rating: SourceRating | None = None

    def __post_init__(self) -> None:
        if self.poll_interval < timedelta(seconds=30):
            msg = f"{self.id}: poll interval must be at least 30 seconds"
            raise ValueError(msg)
        if self.rating is None or (
            self.rating.assessed_grade is not None
            and self.rating.assessed_grade != self.reliability
        ):
            object.__setattr__(self, "rating", source_rating_for(self.id, self.reliability))

    @property
    def independence_key(self) -> str:
        """Sources sharing a parent organisation are not independent for corroboration."""
        return self.parent_organisation or self.organisation
