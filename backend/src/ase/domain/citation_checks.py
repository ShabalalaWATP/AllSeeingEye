"""Bounded literal checks of frozen excerpts, not a semantic entailment or truth test."""

import hashlib
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

METHOD_VERSION = "ase-citation-checks-v1"
MAX_CLAIM_CHARS = 1_600
MAX_SOURCE_CHARS = 20_000
MAX_EXCERPT_CHARS = 1_200
Relation = Literal["supporting", "contradicting"]
SourceField = Literal["title", "summary"]
IndicatorKind = Literal["name_mismatch", "date_mismatch", "number_mismatch", "negation_mismatch"]

LIMITATIONS = (
    "Exact excerpt presence does not establish semantic entailment or the truth of the claim.",
    "Checks use frozen original titles and snippets, not full articles or translated text.",
    "English name, date, number and negation cues are review indicators, "
    "not contradiction findings.",
    "Lexical checks do not resolve aliases, attribution, units, number words, negation scope, "
    "forecasts or missing context. No grade, probability or confidence is changed.",
)


class CitationStatus(StrEnum):
    ABSENT = "absent"
    CONTEXT_INSUFFICIENT = "context_insufficient"
    EXCERPT_PRESENT = "excerpt_present"
    REVIEW_REQUIRED = "review_required"


@dataclass(frozen=True, slots=True)
class ExcerptProposal:
    judgement_id: str
    label: str
    relation: Relation
    field: SourceField
    text: str


@dataclass(frozen=True, slots=True)
class FrozenExcerpt:
    field: SourceField
    start: int
    end: int
    text: str
    sha256: str


@dataclass(frozen=True, slots=True)
class MismatchIndicator:
    kind: IndicatorKind
    claim_values: tuple[str, ...]
    excerpt_values: tuple[str, ...]
    explanation: str


@dataclass(frozen=True, slots=True)
class CitationCheck:
    label: str
    relation: Relation
    status: CitationStatus
    evidence_id: str | None
    source_content_hash: str | None
    excerpt: FrozenExcerpt | None
    indicators: tuple[MismatchIndicator, ...]
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class JudgementCitationCheck:
    judgement_id: str
    status: CitationStatus
    citations: tuple[CitationCheck, ...]
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReportCitationChecks:
    method_version: str
    judgements: tuple[JudgementCitationCheck, ...]
    limitations: tuple[str, ...] = LIMITATIONS


_WORDS = re.compile(r"\b[^\W\d_]+\b", re.UNICODE)
_STOP = frozenset(
    [
        "we",
        "assess",
        "judge",
        "that",
        "it",
        "is",
        "was",
        "were",
        "are",
        "a",
        "an",
        "the",
        "and",
        "or",
        "of",
        "to",
        "in",
        "on",
        "at",
        "for",
        "from",
        "with",
        "by",
        "as",
        "this",
        "these",
        "those",
        "they",
        "them",
        "their",
        "its",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "will",
        "would",
        "should",
        "likely",
        "highly",
        "unlikely",
        "almost",
        "certain",
        "realistic",
        "possibility",
        "chance",
        "remote",
        "probable",
        "not",
        "no",
        "never",
        "without",
        "did",
        "do",
        "does",
        "said",
        "says",
        "officials",
        "report",
        "reported",
        "reports",
    ]
)
_NAME_SKIP = _STOP | frozenset(
    ["president", "minister", "prime", "general", "mr", "mrs", "ms", "dr"]
)
_MONTH_NAMES = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]
_MONTHS = {name.lower(): i for i, name in enumerate(_MONTH_NAMES, 1)}
_MONTHS.update({name[:3].lower(): i for i, name in enumerate(_MONTH_NAMES, 1)})
_MONTHS["sept"] = 9
_MONTH_PATTERN = "(?:" + "|".join(sorted(_MONTHS, key=len, reverse=True)) + ")"
_DATE = re.compile(
    rf"\b(?:(?P<iso>\d{{4}}-\d{{2}}-\d{{2}})|"
    rf"(?P<day>\d{{1,2}})\s+(?P<month>{_MONTH_PATTERN})(?:\s+(?P<year>\d{{4}}))?|"
    rf"(?P<month_first>{_MONTH_PATTERN})\s+(?P<day_last>\d{{1,2}})"
    rf"(?:,?\s+(?P<year_last>\d{{4}}))?)\b",
    re.IGNORECASE,
)
_NUMBER = re.compile(r"(?<![\w.])\d+(?:,\d{3})*(?:\.\d+)?%?(?![\w.])")
_NAME = re.compile(r"\b(?:[A-Z][a-z]+|[A-Z]{2,})\b")
_NEGATION = re.compile(
    r"\b(?:no|not|never|without|cannot|denied|denies|deny)\b|n['\u2019]t\b", re.I
)


def content_words(text: str) -> frozenset[str]:
    return frozenset(word.lower() for word in _WORDS.findall(text) if word.lower() not in _STOP)


def _dates_and_numbers(text: str) -> tuple[frozenset[str], frozenset[str]]:
    dates: set[str] = set()
    remaining = list(text)
    for match in _DATE.finditer(text):
        if match["iso"]:
            dates.add(match["iso"])
        else:
            day = int(match["day"] or match["day_last"])
            month = _MONTHS[(match["month"] or match["month_first"]).lower()]
            year = match["year"] or match["year_last"] or "----"
            dates.add(f"{year}-{month:02}-{day:02}")
        remaining[match.start() : match.end()] = " " * (match.end() - match.start())
    numbers = frozenset(
        match.group().replace(",", "") for match in _NUMBER.finditer("".join(remaining))
    )
    return frozenset(dates), numbers


def mismatch_indicators(claim: str, excerpt: str) -> tuple[MismatchIndicator, ...]:
    """Compare literal cues only when both passages provide comparable values."""
    if len(claim) > MAX_CLAIM_CHARS or len(excerpt) > MAX_EXCERPT_CHARS:
        raise ValueError("The literal-check input exceeds its text limit")
    claim_dates, claim_numbers = _dates_and_numbers(claim)
    excerpt_dates, excerpt_numbers = _dates_and_numbers(excerpt)
    claim_names = frozenset(
        name.casefold()
        for name in _NAME.findall(claim)
        if name.lower() not in _NAME_SKIP and name.lower() not in _MONTHS
    )
    excerpt_names = frozenset(
        name.casefold()
        for name in _NAME.findall(excerpt)
        if name.lower() not in _NAME_SKIP and name.lower() not in _MONTHS
    )
    indicators = []
    comparisons: tuple[tuple[IndicatorKind, frozenset[str], frozenset[str]], ...] = (
        ("name_mismatch", claim_names, excerpt_names),
        ("date_mismatch", claim_dates, excerpt_dates),
        ("number_mismatch", claim_numbers, excerpt_numbers),
    )
    for kind, left, right in comparisons:
        if left and right and not left.issubset(right):
            indicators.append(
                MismatchIndicator(
                    kind,
                    tuple(sorted(left)),
                    tuple(sorted(right)),
                    "Literal values differ or are omitted; "
                    "inspect context before interpreting the difference.",
                )
            )
    negated_claim, negated_excerpt = bool(_NEGATION.search(claim)), bool(_NEGATION.search(excerpt))
    if negated_claim != negated_excerpt:
        indicators.append(
            MismatchIndicator(
                "negation_mismatch",
                ("cue present" if negated_claim else "no cue",),
                ("cue present" if negated_excerpt else "no cue",),
                "Negation cues differ; scope, attribution and double negation are not interpreted.",
            )
        )
    return tuple(indicators)


def exact_excerpt(field: SourceField, text: str, proposed: str) -> FrozenExcerpt | None:
    """Retain exact character offsets; never normalise, translate or repair a proposed quote."""
    if len(text) > MAX_SOURCE_CHARS or not proposed.strip() or len(proposed) > MAX_EXCERPT_CHARS:
        raise ValueError("The proposed excerpt is empty or exceeds its size limit")
    start = text.find(proposed)
    if start == -1:
        return None
    return FrozenExcerpt(
        field,
        start,
        start + len(proposed),
        proposed,
        hashlib.sha256(proposed.encode("utf-8")).hexdigest(),
    )


def select_excerpt(claim: str, field: SourceField, text: str) -> FrozenExcerpt | None:
    """Pick a bounded sentence by lexical overlap, preserving exact original characters."""
    if len(claim) > MAX_CLAIM_CHARS or len(text) > MAX_SOURCE_CHARS:
        raise ValueError("The excerpt-selection input exceeds its text limit")
    candidates = [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", text) if part.strip()]
    bounded = [part for part in candidates if len(part) <= MAX_EXCERPT_CHARS]
    if not bounded:
        return None
    words = content_words(claim)
    chosen = max(bounded, key=lambda part: len(words & content_words(part)))
    return exact_excerpt(field, text, chosen)


def context_reasons(claim: str, excerpt: FrozenExcerpt, language: str | None) -> tuple[str, ...]:
    reasons = []
    if excerpt.field == "title":
        reasons.append(
            "Only an original headline is available; supporting context is insufficient."
        )
    if language is None or language.lower().split("-")[0] != "en":
        reasons.append(
            "English lexical checks are unavailable for unknown or non-English source language."
        )
    words, source_words = content_words(claim), content_words(excerpt.text)
    if len(_WORDS.findall(excerpt.text)) < 8 or len(words & source_words) < 3:
        reasons.append(
            "The excerpt is short or has insufficient lexical overlap with the judgement."
        )
    return tuple(reasons)
