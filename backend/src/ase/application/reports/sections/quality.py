"""Deterministic requirement coverage and gap cleanup for assembled reports."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, replace
from difflib import SequenceMatcher
from enum import StrEnum
from typing import Any

from ase.domain.direction import Direction
from ase.domain.reports import Gap, ReportBody
from ase.domain.research_brief_values import IntelligenceRequirement
from ase.domain.validation import Finding, Severity

MAX_GAPS = 20
_WORDS = re.compile(r"\w+")


class CoverageState(StrEnum):
    ANSWERED = "answered"
    PARTIALLY_ANSWERED = "partially_answered"
    DISPUTED = "disputed"
    NO_ADEQUATE_EVIDENCE = "no_adequate_evidence"


@dataclass(frozen=True, slots=True)
class RequirementCoverage:
    requirement_id: str
    state: CoverageState
    selected_evidence: tuple[str, ...]
    cited_evidence: tuple[str, ...]
    section_ids: tuple[str, ...]
    gap_count: int


def project_requirement_coverage(
    topics: Sequence[tuple[Any, dict[str, Any]]],
    *,
    requirements: Sequence[IntelligenceRequirement] = (),
    direction: Direction | None = None,
    judgements: dict[str, Any] | None = None,
) -> tuple[RequirementCoverage, ...]:
    """Structural coverage for synthesis, not a factual verification of claims.

    Only exact topic bindings and frozen citations count. A selected item alone
    cannot answer a question. A partly answered question remains visible even
    when some evidence was cited; contrary evidence is reported separately.
    """
    if not requirements and not any(topic.requirement_evidence for topic, _ in topics):
        return ()
    ids = (
        tuple(row.id for row in requirements)
        if requirements
        else tuple(f"EEI-{index}" for index in range(1, len(direction.eeis) + 1))
        if direction
        else tuple(
            dict.fromkeys(
                requirement_id
                for topic, _ in topics
                for requirement_id, _ in topic.requirement_evidence
            )
        )
    )
    rows: list[RequirementCoverage] = []
    for requirement_id in ids:
        selected = tuple(
            dict.fromkeys(
                label
                for topic, _ in topics
                for bound_id, labels in topic.requirement_evidence
                if bound_id == requirement_id
                for label in labels
            )
        )
        allowed = frozenset(selected)
        reporting = {
            label
            for _, body in topics
            for item in body["reporting"]
            for label in item["evidence"]
            if label in allowed
        }
        assessment = {
            label
            for _, body in topics
            for item in body["assessment"]
            for label in item["evidence"]
            if label in allowed
        }
        cited = tuple(label for label in selected if label in reporting | assessment)
        section_ids = tuple(
            topic.id
            for topic, body in topics
            if any(
                label in allowed
                for kind in ("reporting", "assessment")
                for item in body[kind]
                for label in item["evidence"]
            )
        )
        gap_count = sum(
            gap.get("eei") == requirement_id for _, body in topics for gap in body["gaps"]
        )
        disputed = any(
            allowed.intersection(row["supporting_evidence"])
            and allowed.intersection(row["contradicting_evidence"])
            for row in (judgements or {}).get("key_judgements", ())
        )
        if not cited:
            state = CoverageState.NO_ADEQUATE_EVIDENCE
        elif disputed:
            state = CoverageState.DISPUTED
        elif reporting and assessment and not gap_count:
            state = CoverageState.ANSWERED
        else:
            state = CoverageState.PARTIALLY_ANSWERED
        rows.append(
            RequirementCoverage(requirement_id, state, selected, cited, section_ids, gap_count)
        )
    return tuple(rows)


def _plain(text: str) -> str:
    return " ".join(_WORDS.findall(text.casefold()))


def _same_gap(first: str, second: str) -> bool:
    left, right = _plain(first), _plain(second)
    if left == right:
        return True
    shorter, longer = sorted((left, right), key=len)
    if len(shorter) >= 60 and longer.startswith(shorter):
        return True
    return SequenceMatcher(None, left, right, autojunk=False).ratio() >= 0.88


def _gap_quality(text: str) -> tuple[bool, bool, int]:
    stripped = text.rstrip()
    # Exact model field limits are a strong truncation signal. Complete sentence
    # endings then take precedence over length when selecting a duplicate.
    not_at_limit = len(stripped) not in {400, 1200}
    complete = bool(stripped) and stripped[-1] in ".!?)]}"
    return complete, not_at_limit, len(stripped)


def _deduplicate(rows: Sequence[Gap]) -> list[Gap]:
    kept: list[Gap] = []
    for row in rows:
        clean = replace(row, text=" ".join(row.text.split()))
        if not clean.text:
            continue
        duplicate = next(
            (
                index
                for index, previous in enumerate(kept)
                if clean.eei == previous.eei and _same_gap(clean.text, previous.text)
            ),
            None,
        )
        if duplicate is None:
            kept.append(clean)
        elif _gap_quality(clean.text) > _gap_quality(kept[duplicate].text):
            kept[duplicate] = clean
    return kept


def normalise_gap_rows(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Clean repeated model gaps before the strict aggregate size check."""
    gaps = _deduplicate(
        tuple(Gap(str(row["text"]), str(row["eei"]) if row.get("eei") else None) for row in rows)
    )
    return [{"text": row.text, "eei": row.eei} for row in gaps[:MAX_GAPS]]


def _notice(question: str, requirement_id: str) -> Gap:
    return Gap(
        f"Not separately assessed from the retained evidence: {question}",
        requirement_id,
    )


def requirement_support_from_topics(
    topics: Sequence[tuple[Any, dict[str, Any]]],
    *,
    requirements: Sequence[IntelligenceRequirement] = (),
    direction: Direction | None = None,
    judgements: dict[str, Any] | None = None,
) -> frozenset[str] | None:
    """Return structurally answered IDs; leave partial/disputed work for review."""
    if not any(topic.requirement_evidence for topic, _ in topics):
        return None
    return frozenset(
        row.requirement_id
        for row in project_requirement_coverage(
            topics, requirements=requirements, direction=direction, judgements=judgements
        )
        if row.state is CoverageState.ANSWERED
    )


def _support_from_body(body: ReportBody, requirement_ids: Sequence[str]) -> frozenset[str]:
    supported: set[str] = set()
    for requirement_id in requirement_ids:
        marker = re.compile(rf"(?<![\w-]){re.escape(requirement_id)}(?![\w-])")
        if any(
            marker.search(theme.theme) and any(item.evidence for item in theme.items)
            for theme in body.reporting
        ):
            supported.add(requirement_id)
        if any(marker.search(section.heading) and section.evidence for section in body.assessment):
            supported.add(requirement_id)
    return frozenset(supported)


def ensure_requirement_coverage(
    body: ReportBody,
    direction: Direction | None,
    *,
    supported: frozenset[str] | None = None,
    requirements: Sequence[IntelligenceRequirement] = (),
) -> tuple[ReportBody, tuple[Finding, ...]]:
    """Add neutral unanswered-EEI notices and return publication review findings.

    A missing answer is described as a limit of the retained packet. It is never
    converted into a claim that the real-world event or condition was absent.
    """
    rows = _deduplicate(body.gaps)
    if requirements:
        requirement_rows = tuple((row.id, row.question, row.required) for row in requirements)
    elif direction is not None:
        requirement_rows = tuple(
            (f"EEI-{index}", question, True) for index, question in enumerate(direction.eeis, 1)
        )
    else:
        requirement_rows = ()
    if not requirement_rows:
        return replace(body, gaps=tuple(rows[:MAX_GAPS])), ()
    requirement_ids = tuple(row[0] for row in requirement_rows)
    questions = {identifier: question for identifier, question, _ in requirement_rows}
    required_ids = {identifier for identifier, _, required in requirement_rows if required}
    supported_ids = (
        _support_from_body(body, requirement_ids) if supported is None else supported
    ) & frozenset(requirement_ids)
    unsupported = tuple(row for row in requirement_ids if row not in supported_ids)
    existing = {row.eei for row in rows if row.eei}
    for requirement_id in unsupported:
        if requirement_id not in existing:
            rows.append(_notice(questions[requirement_id], requirement_id))

    # Keep one disclosure for every unsupported requirement ahead of additional
    # requirement-specific and generic gaps, so the bounded cap cannot hide one.
    priority: list[Gap] = []
    used: set[int] = set()
    for requirement_id in unsupported:
        for index, row in enumerate(rows):
            if row.eei == requirement_id:
                priority.append(row)
                used.add(index)
                break
    required = [
        row for index, row in enumerate(rows) if index not in used and row.eei in requirement_ids
    ]
    other = [
        row
        for index, row in enumerate(rows)
        if index not in used and row.eei not in requirement_ids
    ]
    findings = tuple(
        Finding(
            "requirement_coverage",
            Severity.ERROR,
            requirement_id,
            "The requirement was not separately assessed from sufficient retained evidence.",
        )
        for requirement_id in unsupported
        if requirement_id in required_ids
    )
    return replace(body, gaps=tuple((priority + required + other)[:MAX_GAPS])), findings
