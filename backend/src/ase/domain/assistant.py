"""Transient map answers with explicit scope and server-owned source references."""

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from ase.domain.events import BoundingBox, Point

AssistantScope = Literal["global", "viewport", "selected"]
AssistantKind = Literal["event", "camera", "infrastructure", "gnss"]


@dataclass(frozen=True, slots=True)
class AssistantSelection:
    kind: Literal["event", "camera", "infrastructure"]
    id: str

    def __post_init__(self) -> None:
        if self.kind not in ("event", "camera", "infrastructure") or not (1 <= len(self.id) <= 160):
            raise ValueError("Select a valid map item.")
        if any(ord(char) < 32 for char in self.id):
            raise ValueError("Select a valid map item.")


@dataclass(frozen=True, slots=True)
class AssistantQuestion:
    question: str
    prior_questions: tuple[str, ...] = ()
    scope: AssistantScope = "global"
    bbox: BoundingBox | None = None
    selected: AssistantSelection | None = None

    def __post_init__(self) -> None:
        if len(self.prior_questions) > 4:
            raise ValueError("Use at most four previous questions.")
        for text in (self.question, *self.prior_questions):
            if not 1 <= len(text.strip()) <= 2000 or len(text) > 2000:
                raise ValueError("Questions must contain between 1 and 2,000 characters.")
            if any(ord(char) < 32 and char not in "\n\t" for char in text):
                raise ValueError("Questions contain unsupported control characters.")
        if self.scope not in ("global", "viewport", "selected"):
            raise ValueError("Choose a valid map scope.")
        if (self.scope == "viewport") != (self.bbox is not None):
            raise ValueError("A viewport question requires only its map bounds.")
        if (self.scope == "selected") != (self.selected is not None):
            raise ValueError("A selected-item question requires only its map item.")
        if self.bbox is not None:
            box = self.bbox
            if not all(
                math.isfinite(v) for v in (box.west, box.south, box.east, box.north)
            ) or not (
                -180 <= box.west <= 180
                and -180 <= box.east <= 180
                and -90 <= box.south <= box.north <= 90
            ):
                raise ValueError("Map bounds contain invalid coordinates.")


@dataclass(frozen=True, slots=True)
class AssistantSource:
    id: str
    kind: AssistantKind
    record_id: str
    source_id: str
    title: str
    url: str | None
    published_at: datetime | None
    observed_at: datetime | None
    point: Point | None
    grade: str | None
    summary: str = ""
    details: tuple[str, ...] = ()
    country_iso: str | None = None
    publisher: str | None = None


@dataclass(frozen=True, slots=True)
class AssistantContext:
    sources: tuple[AssistantSource, ...]
    candidate_count: int
    source_count: int
    capped: bool
    notes: tuple[str, ...]
    matched_count: int = 0
    as_of: datetime | None = None
    clarification: str | None = None


@dataclass(frozen=True, slots=True)
class AssistantParagraph:
    kind: Literal["finding", "inference", "gap"]
    text: str
    citations: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AssistantModel:
    name: str
    reasoning_effort: str | None


@dataclass(frozen=True, slots=True)
class AssistantAnswer:
    paragraphs: tuple[AssistantParagraph, ...]
    context: AssistantContext
    question: AssistantQuestion
    generated_at: datetime
    model: AssistantModel | None = None
