"""Mechanical checks of an explicitly cited, frozen original passage.

These checks establish locator integrity and flag literal review cues. Matching a
number or excerpt never establishes that an analytical claim is true.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from ase.domain.citation_checks import mismatch_indicators
from ase.domain.validation_types import Finding, Severity

MAX_PASSAGES = 40
MAX_LINKS = 20
MAX_PASSAGE_CHARS = 1_800
MAX_QUOTE_CHARS = 1_200
_UNIT = re.compile(
    r"(?<![\w.])(?P<number>\d+(?:,\d{3})*(?:\.\d+)?)\s*"
    r"(?P<unit>kilometres?|km|miles?|tonnes?|kilograms?|kg|megawatts?|mw|"
    r"gigawatts?|gw|hours?|days?)(?!\w)",
    re.IGNORECASE,
)
_GENERIC_RESOLUTION = frozenset(
    {"because", "unknown", "uncertain", "resolved", "observe", "check later", "see what happens"}
)
_UNIT_ALIASES = {
    "kilometre": "km",
    "kilometres": "km",
    "mile": "miles",
    "miles": "miles",
    "tonne": "tonnes",
    "tonnes": "tonnes",
    "kilogram": "kg",
    "kilograms": "kg",
    "megawatt": "mw",
    "megawatts": "mw",
    "gigawatt": "gw",
    "gigawatts": "gw",
    "hour": "hours",
    "hours": "hours",
    "day": "days",
    "days": "days",
}


@dataclass(frozen=True, slots=True)
class FrozenClaimPassage:
    id: str
    document_version_id: str
    evidence_label: str
    text_sha256: str
    text: str = field(repr=False)
    language: str | None = None


@dataclass(frozen=True, slots=True)
class ClaimPassageCitation:
    passage_id: str
    document_version_id: str
    evidence_label: str
    start: int
    end: int
    excerpt: str = field(repr=False)
    relation: Literal["supporting", "opposing", "context"] = "supporting"


def _unit_pairs(text: str) -> dict[str, set[str]]:
    pairs: dict[str, set[str]] = {}
    for match in _UNIT.finditer(text):
        number = match["number"].replace(",", "")
        unit = match["unit"].casefold()
        pairs.setdefault(number, set()).add(_UNIT_ALIASES.get(unit, unit))
    return pairs


def _integrity(passage: FrozenClaimPassage) -> bool:
    return (
        bool(passage.id)
        and bool(passage.document_version_id)
        and bool(passage.evidence_label)
        and 1 <= len(passage.text) <= MAX_PASSAGE_CHARS
        and hashlib.sha256(passage.text.encode("utf-8")).hexdigest() == passage.text_sha256
    )


def check_claim_passages(
    claim_id: str,
    claim_text: str,
    citations: Sequence[ClaimPassageCitation],
    passages: Mapping[str, FrozenClaimPassage],
    evidence_labels: frozenset[str],
) -> tuple[Finding, ...]:
    """Reject invented/misaligned locators; flag English literal mismatches for review.

    The caller must supply authorised, exact-version frozen passages. No fetch or
    current-source lookup takes place here. A non-English/unknown-language passage
    can pass the exact locator check, but lexical comparisons remain unassessed.
    """
    if (
        not 1 <= len(claim_text) <= 1_600
        or len(citations) > MAX_LINKS
        or len(passages) > MAX_PASSAGES
    ):
        raise ValueError("Claim passage check exceeds its bounded input")
    if not citations:
        return (
            Finding("citation", Severity.ERROR, claim_id, "No original passage citation supplied"),
        )
    findings: list[Finding] = []
    seen: set[tuple[str, int, int, str]] = set()
    for citation in citations:
        identity = (citation.passage_id, citation.start, citation.end, citation.relation)
        if identity in seen:
            findings.append(
                Finding("citation", Severity.ERROR, claim_id, "Duplicate passage citation")
            )
            continue
        seen.add(identity)
        passage = passages.get(citation.passage_id)
        if passage is None or citation.evidence_label not in evidence_labels:
            findings.append(
                Finding("citation", Severity.ERROR, claim_id, "Cited frozen passage is unavailable")
            )
            continue
        if not _integrity(passage):
            findings.append(
                Finding(
                    "passage_integrity",
                    Severity.ERROR,
                    claim_id,
                    "Frozen passage hash or identity is invalid",
                )
            )
            continue
        if (
            passage.id != citation.passage_id
            or passage.document_version_id != citation.document_version_id
            or passage.evidence_label != citation.evidence_label
            or citation.relation not in {"supporting", "opposing", "context"}
            or type(citation.start) is not int
            or type(citation.end) is not int
            or not 0 <= citation.start < citation.end <= len(passage.text)
            or citation.end - citation.start > MAX_QUOTE_CHARS
            or passage.text[citation.start : citation.end] != citation.excerpt
        ):
            findings.append(
                Finding(
                    "citation",
                    Severity.ERROR,
                    claim_id,
                    "Citation does not match its frozen passage locator",
                )
            )
            continue
        if not passage.language or passage.language.casefold().split("-")[0] != "en":
            findings.append(
                Finding(
                    "passage_language",
                    Severity.WARNING,
                    claim_id,
                    "Literal comparison is unavailable for this original language",
                )
            )
            continue
        for indicator in mismatch_indicators(claim_text, citation.excerpt):
            if indicator.kind in {
                "name_mismatch",
                "number_mismatch",
                "date_mismatch",
                "negation_mismatch",
            }:
                findings.append(
                    Finding(
                        "literal_review",
                        Severity.WARNING,
                        claim_id,
                        f"{indicator.kind}: inspect attribution and context in the exact passage",
                    )
                )
        claim_units, excerpt_units = _unit_pairs(claim_text), _unit_pairs(citation.excerpt)
        for number in sorted(claim_units.keys() & excerpt_units.keys()):
            if claim_units[number].isdisjoint(excerpt_units[number]):
                findings.append(
                    Finding(
                        "literal_review",
                        Severity.WARNING,
                        claim_id,
                        f"unit_mismatch for {number}: inspect the exact passage and any conversion",
                    )
                )
    return tuple(findings)


def check_forecast_fields(
    claim_id: str,
    *,
    kind: Literal["observation", "attributed_claim", "judgement", "forecast"],
    issued_at: datetime,
    horizon_end: datetime | None,
    resolution_criterion: str | None,
    review_at: datetime | None,
) -> tuple[Finding, ...]:
    """Validate explicit forecast metadata when a caller's claim schema carries it."""
    if kind not in {"observation", "attributed_claim", "judgement", "forecast"}:
        raise ValueError("Unknown claim kind")
    if issued_at.utcoffset() is None:
        raise ValueError("Issue time must be timezone-aware")
    if kind != "forecast":
        return ()
    findings = []
    if horizon_end is None or horizon_end.utcoffset() is None or horizon_end <= issued_at:
        findings.append(
            Finding("forecast", Severity.ERROR, claim_id, "Forecast needs a future, dated horizon")
        )
    criterion = re.sub(r"[^\w]+", " ", (resolution_criterion or "").casefold()).strip()
    if not criterion or criterion in _GENERIC_RESOLUTION:
        findings.append(
            Finding(
                "forecast",
                Severity.ERROR,
                claim_id,
                "Forecast needs an observable resolution criterion",
            )
        )
    if review_at is None or review_at.utcoffset() is None or review_at < issued_at:
        findings.append(
            Finding("forecast", Severity.ERROR, claim_id, "Forecast needs a dated review time")
        )
    return tuple(findings)
