"""Frozen evidence: the items a report may cite, and the quality-of-information statistics.

An evidence item is a snapshot of an event at generation time (docs/03 section 12), so
the report still means the same thing after the live store has moved on.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime

from ase.domain.doctrine import Confidence
from ase.domain.events import Credibility, Event

# Phrases that read as instructions to the model rather than as reporting.
INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"ignore (all |any |the )?(previous|prior|above|earlier) (instructions|prompts?|context)",
        r"disregard (all |any |the )?(previous|prior|above) (instructions|prompts?)",
        r"\bsystem prompt\b",
        r"\byou are now\b",
        r"\bnew instructions?\b:",
        r"\bas an ai\b",
        r"\b(assistant|system|user)\s*:\s",
        r"<\s*/?\s*(system|assistant|instruction)\s*>",
        r"\bdo not (follow|obey) (the )?(rules|instructions)\b",
        r"\breveal (your|the) (system )?prompt\b",
    )
)


def injection_flags(*texts: str | None) -> tuple[str, ...]:
    """The instruction-like phrases found in the texts, lower-cased and de-duplicated."""
    found: list[str] = []
    for text in texts:
        if not text:
            continue
        for pattern in INJECTION_PATTERNS:
            match = pattern.search(text)
            if match is not None and match.group(0).lower() not in found:
                found.append(match.group(0).lower())
    return tuple(found)


@dataclass(frozen=True, slots=True)
class EvidenceItem:
    label: str
    event_id: str
    source_id: str
    source_name: str
    independence_key: str
    category: str
    title: str
    summary: str | None
    url: str | None
    published_at: datetime
    captured_at: datetime
    grade: str
    reliability: str
    credibility: int
    grade_rationale: str
    lon: float | None
    lat: float | None
    country_iso: str | None
    content_hash: str
    instrument: bool = False
    flags: tuple[str, ...] = ()

    @classmethod
    def from_event(
        cls,
        label: str,
        event: Event,
        captured_at: datetime,
        *,
        source_name: str,
        independence_key: str,
        instrument: bool = False,
        flags: Sequence[str] = (),
    ) -> EvidenceItem:
        return cls(
            label=label,
            event_id=event.id,
            source_id=event.source_id,
            source_name=source_name,
            independence_key=independence_key,
            category=event.category.value,
            title=event.title,
            summary=event.summary,
            url=event.url,
            published_at=event.published_at,
            captured_at=captured_at,
            grade=event.grade,
            reliability=event.reliability.value,
            credibility=int(event.credibility),
            grade_rationale=event.grade_rationale,
            lon=event.point.lon if event.point else None,
            lat=event.point.lat if event.point else None,
            country_iso=event.country_iso,
            content_hash=event.content_hash,
            instrument=instrument,
            flags=tuple(flags),
        )


@dataclass(frozen=True, slots=True)
class QualityOfInformation:
    """What the analyst (and the model) should know about the evidence before reading it."""

    items: int
    by_grade: dict[str, int] = field(default_factory=dict)
    independent_organisations: int = 0
    instrument_share: float = 0.0
    newest: datetime | None = None
    oldest: datetime | None = None
    contradictions: int = 0
    flagged: int = 0
    confidence_ceiling: Confidence = Confidence.HIGH

    def describe(self) -> str:
        grades = ", ".join(f"{count} {grade}" for grade, count in sorted(self.by_grade.items()))
        return (
            f"{self.items} evidence items ({grades or 'none'}) from "
            f"{self.independent_organisations} independent organisation(s); "
            f"{round(self.instrument_share * 100)}% instrument data; "
            f"{self.contradictions} contradiction(s); {self.flagged} item(s) flagged for "
            f"instruction-like text; confidence ceiling {self.confidence_ceiling.value}."
        )


def quality_of_information(items: Sequence[EvidenceItem], flagged: int = 0) -> QualityOfInformation:
    if not items:
        return QualityOfInformation(items=0, confidence_ceiling=Confidence.LOW, flagged=flagged)
    by_grade: dict[str, int] = {}
    for item in items:
        by_grade[item.grade] = by_grade.get(item.grade, 0) + 1
    organisations = {item.independence_key for item in items}
    instruments = sum(1 for item in items if item.instrument)
    weak = all(item.credibility >= int(Credibility.POSSIBLY_TRUE) for item in items)
    ceiling = Confidence.MODERATE if weak or len(organisations) < 2 else Confidence.HIGH
    if len(items) < 3 and ceiling is Confidence.MODERATE:
        ceiling = Confidence.LOW
    published = [item.published_at for item in items]
    return QualityOfInformation(
        items=len(items),
        by_grade=by_grade,
        independent_organisations=len(organisations),
        instrument_share=instruments / len(items),
        newest=max(published),
        oldest=min(published),
        contradictions=0,
        flagged=flagged,
        confidence_ceiling=ceiling,
    )
