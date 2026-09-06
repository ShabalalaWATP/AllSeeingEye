"""Bounded question and collection records, independent of providers and storage."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from ase.domain.events import Event
from ase.domain.languages import valid_language_code
from ase.domain.research_plan import QueryVariant, ResearchPlan


class ResearchMode(StrEnum):
    QUICK = "quick"
    DETAILED = "detailed"


class ResearchFocus(StrEnum):
    GENERAL = "general"
    COMPANY = "company"
    DOMAIN = "domain"
    DOCUMENT = "document"
    MEDIA = "media"


class CollectionStatus(StrEnum):
    COMPLETED = "completed"
    EMPTY = "empty"
    UNAVAILABLE = "unavailable"
    UNSUPPORTED = "unsupported"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    BUDGET_EXHAUSTED = "budget_exhausted"


@dataclass(frozen=True, slots=True)
class ResearchQuery:
    question: str
    since: datetime
    until: datetime
    languages: tuple[str, ...] = ("en",)
    terms: tuple[str, ...] = ()
    mode: ResearchMode = ResearchMode.QUICK
    focus: ResearchFocus = ResearchFocus.GENERAL
    country_iso: str | None = None
    subject: str | None = None
    source_ids: tuple[str, ...] | None = None
    query_variants: tuple[QueryVariant, ...] = ()

    def __post_init__(self) -> None:
        if self.source_ids is not None and (
            len(self.source_ids) > 64
            or len(set(self.source_ids)) != len(self.source_ids)
            or any(not value or len(value) > 120 for value in self.source_ids)
        ):
            raise ValueError("Select at most 64 unique collection sources")
        variant_languages = [variant.language.lower() for variant in self.query_variants]
        if len(variant_languages) > 8 or len(set(variant_languages)) != len(variant_languages):
            raise ValueError("Provide at most one query variant per language")
        if not set(variant_languages).issubset(value.lower() for value in self.languages):
            raise ValueError("Query variants must use selected research languages")
        if any(not valid_language_code(value) for value in self.languages):
            raise ValueError("Invalid research language code")
        object.__setattr__(
            self, "languages", tuple(dict.fromkeys(value.lower() for value in self.languages))
        )
        if not self.question.strip() or len(self.question) > 2000:
            raise ValueError("Question must contain between 1 and 2000 characters")
        if any(value.utcoffset() is None for value in (self.since, self.until)):
            raise ValueError("Research dates must include a timezone")
        if self.since >= self.until:
            raise ValueError("Research start must precede end")
        if not 1 <= len(self.languages) <= 8 or any(
            not value or len(value) > 16 for value in self.languages
        ):
            raise ValueError("Provide between one and eight language codes")
        if len(self.terms) > 12 or any(not term.strip() or len(term) > 300 for term in self.terms):
            raise ValueError("Provide at most twelve bounded search terms")
        if self.subject is not None and len(self.subject) > 300:
            raise ValueError("Subject exceeds 300 characters")


@dataclass(frozen=True, slots=True)
class CollectionAttempt:
    source_id: str
    source_name: str
    status: CollectionStatus
    result_count: int = 0
    explanation: str = ""
    language: str | None = None

    def __post_init__(self) -> None:
        if not self.source_id or len(self.source_id) > 120 or len(self.source_name) > 200:
            raise ValueError("Invalid collection source identity")
        if not 0 <= self.result_count <= 1000 or len(self.explanation) > 1000:
            raise ValueError("Collection receipt exceeds its bounds")


@dataclass(frozen=True, slots=True)
class CollectionPass:
    terms: tuple[str, ...]
    attempts: tuple[CollectionAttempt, ...]
    plan: ResearchPlan | None = None

    def __post_init__(self) -> None:
        if len(self.attempts) > 64 or len(self.terms) > 12:
            raise ValueError("Collection pass exceeds its bounds")


@dataclass(frozen=True, slots=True)
class ResearchBatch:
    items: tuple[Event, ...] = ()
    attempts: tuple[CollectionAttempt, ...] = ()
    plan: ResearchPlan | None = None
    passes: tuple[CollectionPass, ...] = ()

    def __post_init__(self) -> None:
        if len(self.passes) > 2:
            raise ValueError("At most two collection passes are supported")
        if len(self.items) > 1000 or len(self.attempts) > 64:
            raise ValueError("Research batch exceeds its bounds")
