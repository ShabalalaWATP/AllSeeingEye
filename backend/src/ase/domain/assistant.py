"""Transient map answers with explicit scope and server-owned source references."""

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from ase.domain.events import BoundingBox, Category, Point

AssistantScope = Literal["global", "viewport", "selected", "report"]
AssistantKind = Literal[
    "event", "camera", "infrastructure", "gnss", "doctrine", "report_claim", "report_evidence"
]


@dataclass(frozen=True, slots=True)
class AssistantReportSelection:
    id: UUID
    version: int

    def __post_init__(self) -> None:
        if type(self.version) is not int or not 1 <= self.version <= 1_000_000:
            raise ValueError("Select an exact report version.")


@dataclass(frozen=True, slots=True)
class AssistantReportContext:
    id: UUID
    version_id: UUID
    version: int
    title: str
    data_cutoff: datetime | None


@dataclass(frozen=True, slots=True)
class AssistantTimeRange:
    since: datetime
    until: datetime

    def __post_init__(self) -> None:
        if (
            self.since.tzinfo is None
            or self.until.tzinfo is None
            or self.since.utcoffset() is None
            or self.until.utcoffset() is None
            or self.since >= self.until
            or (self.until - self.since).total_seconds() > 366 * 86400
        ):
            raise ValueError("Choose a valid time range of at most 366 days.")


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
    time_range: AssistantTimeRange | None = None
    continuation_id: str | None = None
    source_categories: tuple[str, ...] | None = None
    report: AssistantReportSelection | None = None

    def __post_init__(self) -> None:
        if len(self.prior_questions) > 4:
            raise ValueError("Use at most four previous questions.")
        if self.continuation_id is not None and not (
            16 <= len(self.continuation_id) <= 80
            and all(
                char.isascii() and (char.isalnum() or char in "-_") for char in self.continuation_id
            )
        ):
            raise ValueError("Choose a valid conversation reference.")
        if self.source_categories is not None and (
            not 1 <= len(self.source_categories) <= len(Category) + 3
            or len(set(self.source_categories)) != len(self.source_categories)
            or any(
                category
                not in {value.value for value in Category}
                | {"camera", "infrastructure", "doctrine"}
                for category in self.source_categories
            )
        ):
            raise ValueError("Choose valid, distinct source categories.")
        for text in (self.question, *self.prior_questions):
            if not 1 <= len(text.strip()) <= 2000 or len(text) > 2000:
                raise ValueError("Questions must contain between 1 and 2,000 characters.")
            if any(ord(char) < 32 and char not in "\n\t" for char in text):
                raise ValueError("Questions contain unsupported control characters.")
        if self.scope not in ("global", "viewport", "selected", "report"):
            raise ValueError("Choose a valid map scope.")
        if (self.scope == "viewport") != (self.bbox is not None):
            raise ValueError("A viewport question requires only its map bounds.")
        if (self.scope == "selected") != (self.selected is not None):
            raise ValueError("A selected-item question requires only its map item.")
        self._validate_report_scope()
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

    def _validate_report_scope(self) -> None:
        if (self.scope == "report") != (self.report is not None):
            raise ValueError("A report question requires an exact report version.")
        if self.scope == "report" and (
            self.time_range is not None
            or self.source_categories is not None
            or self.continuation_id is not None
        ):
            raise ValueError("Report questions use only the selected frozen edition.")


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
class AssistantInterpretation:
    topics: tuple[str, ...]
    countries: tuple[str, ...]
    since: datetime | None = None
    until: datetime | None = None
    time_basis: Literal["publication"] = "publication"
    notes: tuple[str, ...] = ()
    source_categories: tuple[str, ...] = ()


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
    interpretation: AssistantInterpretation | None = None
    report: AssistantReportContext | None = None


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
    continuation_id: str | None = None
