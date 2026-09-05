"""The report as a value object (docs/03 section 10) and the JSON schema the model must fill.

The header is written by the engine; the model produces only the body. Parsing is
lenient about unknown fields (they are dropped) and strict about types, so a model that
wanders off the schema produces findings rather than crashes.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from ase.domain.doctrine import Confidence, Probability

MAX_JUDGEMENT_CHARS = 400
MAX_ITEM_CHARS = 1_200
MAX_SECTION_CHARS = 4_000
MAX_LIST = 20


class ReportStatus(StrEnum):
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"


class ChangeFromPrevious(StrEnum):
    NEW = "new"
    UNCHANGED = "unchanged"
    STRENGTHENED = "strengthened"
    WEAKENED = "weakened"
    REVERSED = "reversed"


class WatchCondition(StrEnum):
    NORMAL = "normal"
    ELEVATED = "elevated"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class KeyJudgement:
    id: str
    statement: str
    probability: Probability
    confidence: Confidence
    confidence_statement: str
    supporting_evidence: tuple[str, ...] = ()
    contradicting_evidence: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    change_from_previous: ChangeFromPrevious | None = None
    indicators: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ReportingItem:
    text: str
    evidence: tuple[str, ...] = ()
    grade: str = ""


@dataclass(frozen=True, slots=True)
class ReportingTheme:
    theme: str
    items: tuple[ReportingItem, ...] = ()


@dataclass(frozen=True, slots=True)
class AssessmentSection:
    heading: str
    text: str
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Assumption:
    id: str
    text: str
    lynchpin: bool = False


@dataclass(frozen=True, slots=True)
class AlternativeHypothesis:
    text: str
    why_less_likely: str
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class IndicatorsAndWarning:
    watch_condition: WatchCondition = WatchCondition.NORMAL
    changes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Gap:
    text: str
    eei: str | None = None


@dataclass(frozen=True, slots=True)
class ReportBody:
    key_judgements: tuple[KeyJudgement, ...] = ()
    reporting: tuple[ReportingTheme, ...] = ()
    assessment: tuple[AssessmentSection, ...] = ()
    assumptions: tuple[Assumption, ...] = ()
    alternative_hypotheses: tuple[AlternativeHypothesis, ...] = ()
    indicators_and_warning: IndicatorsAndWarning = field(default_factory=IndicatorsAndWarning)
    gaps: tuple[Gap, ...] = ()
    collection_recommendations: tuple[str, ...] = ()
    sourcing_statement: str = ""

    def cited_labels(self) -> frozenset[str]:
        labels: set[str] = set()
        for judgement in self.key_judgements:
            labels.update(judgement.supporting_evidence, judgement.contradicting_evidence)
        for theme in self.reporting:
            for item in theme.items:
                labels.update(item.evidence)
        for section in self.assessment:
            labels.update(section.evidence)
        for alternative in self.alternative_hypotheses:
            labels.update(alternative.evidence)
        return frozenset(labels)

    def texts(self) -> list[str]:
        """Every free-text field the model wrote, for the linters that scan prose."""
        parts: list[str] = [self.sourcing_statement]
        for judgement in self.key_judgements:
            parts.extend(
                [judgement.statement, judgement.confidence_statement, *judgement.indicators]
            )
        for theme in self.reporting:
            parts.extend(item.text for item in theme.items)
        for section in self.assessment:
            parts.append(section.text)
        parts.extend(a.text for a in self.assumptions)
        for alternative in self.alternative_hypotheses:
            parts.extend([alternative.text, alternative.why_less_likely])
        parts.extend(self.indicators_and_warning.changes)
        parts.extend(gap.text for gap in self.gaps)
        parts.extend(self.collection_recommendations)
        return [part for part in parts if part]


@dataclass(frozen=True, slots=True)
class ReportHeader:
    template: str
    title: str
    scope: Mapping[str, Any]
    period_from: datetime
    period_to: datetime
    data_cutoff: datetime
    requirements: tuple[str, ...] = ()


class ReportParseError(ValueError):
    """The model's JSON does not fit the body schema; the message names the field."""


def _str(value: object, field_name: str, limit: int) -> str:
    if not isinstance(value, str):
        raise ReportParseError(f"{field_name} must be a string")
    return value.strip()[:limit]


def _labels(value: object, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ReportParseError(f"{field_name} must be a list")
    return tuple(_str(item, field_name, 32) for item in value)[:MAX_LIST]


def _strings(value: object, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ReportParseError(f"{field_name} must be a list")
    return tuple(_str(item, field_name, MAX_ITEM_CHARS) for item in value)[:MAX_LIST]


def _objects(value: object, field_name: str) -> list[Mapping[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ReportParseError(f"{field_name} must be a list of objects")
    return list(value)[:MAX_LIST]


def _enum(value: object, choices: type[StrEnum], field_name: str) -> Any:
    try:
        return choices(str(value).strip().lower())
    except ValueError as exc:
        raise ReportParseError(f"{field_name} must be one of {[c.value for c in choices]}") from exc


def _judgement(item: Mapping[str, Any], index: int) -> KeyJudgement:
    change = item.get("change_from_previous")
    return KeyJudgement(
        id=_str(item.get("id", f"KJ{index}"), "key_judgements.id", 16) or f"KJ{index}",
        statement=_str(item.get("statement", ""), "key_judgements.statement", MAX_JUDGEMENT_CHARS),
        probability=_enum(item.get("probability"), Probability, "key_judgements.probability"),
        confidence=_enum(item.get("confidence"), Confidence, "key_judgements.confidence"),
        confidence_statement=_str(
            item.get("confidence_statement", ""), "confidence_statement", MAX_ITEM_CHARS
        ),
        supporting_evidence=_labels(item.get("supporting_evidence"), "supporting_evidence"),
        contradicting_evidence=_labels(
            item.get("contradicting_evidence"), "contradicting_evidence"
        ),
        assumptions=_labels(item.get("assumptions"), "assumptions"),
        change_from_previous=None
        if change in (None, "")
        else _enum(change, ChangeFromPrevious, "change_from_previous"),
        indicators=_strings(item.get("indicators"), "indicators"),
    )


def parse_body(data: Any) -> ReportBody:
    """Turn the model's JSON into a ReportBody, dropping unknown fields, bounding lengths."""
    if not isinstance(data, dict):
        raise ReportParseError("the report must be a JSON object")
    judgements = tuple(
        _judgement(item, index + 1)
        for index, item in enumerate(_objects(data.get("key_judgements"), "key_judgements"))
    )
    reporting = tuple(
        ReportingTheme(
            theme=_str(theme.get("theme", ""), "reporting.theme", 120),
            items=tuple(
                ReportingItem(
                    text=_str(item.get("text", ""), "reporting.items.text", MAX_ITEM_CHARS),
                    evidence=_labels(item.get("evidence"), "reporting.items.evidence"),
                    grade=_str(item.get("grade", ""), "reporting.items.grade", 4),
                )
                for item in _objects(theme.get("items"), "reporting.items")
            ),
        )
        for theme in _objects(data.get("reporting"), "reporting")
    )
    assessment = tuple(
        AssessmentSection(
            heading=_str(section.get("heading", ""), "assessment.heading", 120),
            text=_str(section.get("text", ""), "assessment.text", MAX_SECTION_CHARS),
            evidence=_labels(section.get("evidence"), "assessment.evidence"),
        )
        for section in _objects(data.get("assessment"), "assessment")
    )
    assumptions = tuple(
        Assumption(
            id=_str(item.get("id", f"A{index + 1}"), "assumptions.id", 16) or f"A{index + 1}",
            text=_str(item.get("text", ""), "assumptions.text", MAX_ITEM_CHARS),
            lynchpin=bool(item.get("lynchpin", False)),
        )
        for index, item in enumerate(_objects(data.get("assumptions"), "assumptions"))
    )
    alternatives = tuple(
        AlternativeHypothesis(
            text=_str(item.get("text", ""), "alternative_hypotheses.text", MAX_ITEM_CHARS),
            why_less_likely=_str(
                item.get("why_less_likely", ""), "why_less_likely", MAX_ITEM_CHARS
            ),
            evidence=_labels(item.get("evidence"), "alternative_hypotheses.evidence"),
        )
        for item in _objects(data.get("alternative_hypotheses"), "alternative_hypotheses")
    )
    warning_raw = data.get("indicators_and_warning")
    if warning_raw is None:
        warning_raw = {}
    if not isinstance(warning_raw, dict):
        raise ReportParseError("indicators_and_warning must be an object")
    warning = IndicatorsAndWarning(
        watch_condition=_enum(
            warning_raw.get("watch_condition", "normal"), WatchCondition, "watch_condition"
        ),
        changes=_strings(warning_raw.get("changes"), "indicators_and_warning.changes"),
    )
    gaps = tuple(
        Gap(
            text=_str(item.get("text", ""), "gaps.text", MAX_ITEM_CHARS),
            eei=_str(item["eei"], "gaps.eei", 32) if item.get("eei") else None,
        )
        for item in _objects(data.get("gaps"), "gaps")
    )
    return ReportBody(
        key_judgements=judgements,
        reporting=reporting,
        assessment=assessment,
        assumptions=assumptions,
        alternative_hypotheses=alternatives,
        indicators_and_warning=warning,
        gaps=gaps,
        collection_recommendations=_strings(
            data.get("collection_recommendations"), "collection_recommendations"
        ),
        sourcing_statement=_str(
            data.get("sourcing_statement", ""), "sourcing_statement", MAX_SECTION_CHARS
        ),
    )
