"""Frozen, deterministic source tasks; no generated translations or fetch URLs."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from ase.domain.languages import valid_language_code

UNKNOWN_TEMPORAL_SCOPE = (
    "Bounded available records only; complete historical coverage is not established."
)


@dataclass(frozen=True, slots=True)
class QueryVariant:
    language: str
    terms: tuple[str, ...]

    def __post_init__(self) -> None:
        if not valid_language_code(self.language):
            raise ValueError("Invalid query variant language")
        if (
            not 1 <= len(self.terms) <= 12
            or any(not term.strip() or len(term) > 300 for term in self.terms)
            or sum(map(len, self.terms)) > 1000
        ):
            raise ValueError("Query variants require bounded explicit terms")


@dataclass(frozen=True, slots=True)
class QueryTransformation:
    original_terms: tuple[str, ...]
    languages: tuple[str, ...]
    model: str
    status: Literal["completed", "failed", "unavailable"]
    variants: tuple[QueryVariant, ...] = ()
    policy_version: str = "ase-query-translation-v1"


@dataclass(frozen=True, slots=True)
class ResearchTask:
    source_id: str
    source_name: str
    selected: bool
    supported: bool
    language: str | None
    terms: tuple[str, ...]
    provenance: str
    temporal_scope: str = UNKNOWN_TEMPORAL_SCOPE
    query_language: str | None = None


@dataclass(frozen=True, slots=True)
class ResearchPlan:
    question: str
    since: datetime
    until: datetime
    languages: tuple[str, ...]
    tasks: tuple[ResearchTask, ...]
    request_limit: int
    seconds_limit: float
    item_limit: int
    policy_version: str = "ase-deterministic-plan-v1"
    model_calls: int = 0
    translation_calls: int = 0
    replans: int = 0
    focus: str = "general"
    mode: str = "quick"
    subject: str | None = None
    country_iso: str | None = None
    translation: QueryTransformation | None = None
