"""Deterministic requirement coverage and gap cleanup for assembled reports."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import replace
from difflib import SequenceMatcher
from typing import Any

from ase.domain.direction import Direction
from ase.domain.reports import Gap, ReportBody
from ase.domain.validation import Finding, Severity

MAX_GAPS = 20
_WORDS = re.compile(r"\w+")


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


def _requirement_text(direction: Direction, requirement_id: str) -> str:
    index = int(requirement_id.removeprefix("EEI-")) - 1
    return direction.eeis[index]


def _notice(direction: Direction, requirement_id: str) -> Gap:
    question = _requirement_text(direction, requirement_id)
    return Gap(
        f"Not separately assessed from the retained evidence: {question}",
        requirement_id,
    )


def requirement_support_from_topics(
    topics: Sequence[tuple[Any, dict[str, Any]]],
) -> frozenset[str] | None:
    """Return explicit v3 support, or defer legacy topics to body-heading inference."""
    if not any(topic.requirement_evidence for topic, _ in topics):
        return None
    supported: set[str] = set()
    for topic, body in topics:
        cited = {
            label
            for section in (body["reporting"], body["assessment"])
            for row in section
            for label in row.get("evidence", ())
        }
        for requirement_id, evidence_labels in topic.requirement_evidence:
            if cited & set(evidence_labels):
                supported.add(requirement_id)
    return frozenset(supported)


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
) -> tuple[ReportBody, tuple[Finding, ...]]:
    """Add neutral unanswered-EEI notices and return publication review findings.

    A missing answer is described as a limit of the retained packet. It is never
    converted into a claim that the real-world event or condition was absent.
    """
    rows = _deduplicate(body.gaps)
    if direction is None or not direction.eeis:
        return replace(body, gaps=tuple(rows[:MAX_GAPS])), ()
    requirement_ids = tuple(f"EEI-{index}" for index in range(1, len(direction.eeis) + 1))
    supported_ids = (
        _support_from_body(body, requirement_ids) if supported is None else supported
    ) & frozenset(requirement_ids)
    unsupported = tuple(row for row in requirement_ids if row not in supported_ids)
    existing = {row.eei for row in rows if row.eei}
    for requirement_id in unsupported:
        if requirement_id not in existing:
            rows.append(_notice(direction, requirement_id))

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
    )
    return replace(body, gaps=tuple((priority + required + other)[:MAX_GAPS])), findings
