"""Every requirement the direction call raised is answered, or is listed as uncovered.

The section pipeline already adds a neutral gap notice for an unanswered EEI and an
error for a required one. It does not look at the PIR or the SIRs, so a report could
answer none of them and still read as complete. This gate closes that: each PIR, SIR
and EEI is answered in the report, disclosed as a gap, or named as uncovered with the
reason. It reads the finished body and changes nothing in it.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from ase.domain.direction import Direction
from ase.domain.report_quality_rules import REQUIREMENT_COVERAGE_RULE, REQUIREMENT_GATE_RULE
from ase.domain.reports import ReportBody
from ase.domain.research_brief_values import IntelligenceRequirement
from ase.domain.validation_types import Finding, Severity

# A requirement counts as addressed when most of its content words appear in the prose.
OVERLAP_THRESHOLD = 0.6
MIN_WORD_CHARS = 4
_WORDS = re.compile(r"[A-Za-z][A-Za-z'-]{2,}")
_STOPWORDS = frozenset(
    {
        "what",
        "when",
        "where",
        "which",
        "will",
        "does",
        "have",
        "been",
        "there",
        "their",
        "this",
        "that",
        "with",
        "from",
        "into",
        "over",
        "about",
        "much",
        "many",
        "more",
        "most",
        "they",
        "them",
        "these",
        "those",
        "any",
        "are",
        "has",
        "how",
    }
)


def _content_words(text: str) -> set[str]:
    return {
        word.casefold()
        for word in _WORDS.findall(text)
        if len(word) >= MIN_WORD_CHARS and word.casefold() not in _STOPWORDS
    }


def requirement_rows(
    direction: Direction | None,
    requirements: Sequence[IntelligenceRequirement],
) -> tuple[tuple[str, str], ...]:
    """Every requirement identifier with its question, authored or directed."""
    if requirements:
        return tuple((row.id, row.question) for row in requirements)
    if direction is None:
        return ()
    return (
        ("PIR-1", direction.pir),
        *((f"SIR-{index}", text) for index, text in enumerate(direction.sirs, 1)),
        *((f"EEI-{index}", text) for index, text in enumerate(direction.eeis, 1)),
    )


def _named_in_headings(body: ReportBody, requirement_id: str) -> bool:
    marker = re.compile(rf"(?<![\w-]){re.escape(requirement_id)}(?![\w-])")
    return any(
        marker.search(theme.theme) and any(item.evidence for item in theme.items)
        for theme in body.reporting
    ) or any(marker.search(section.heading) and section.evidence for section in body.assessment)


def _prose_words(body: ReportBody) -> set[str]:
    return _content_words(" ".join(body.texts()))


def _answered(body: ReportBody, requirement_id: str, question: str, prose: set[str]) -> bool:
    if _named_in_headings(body, requirement_id):
        return True
    if requirement_id == "PIR-1" and any(
        judgement.supporting_evidence for judgement in body.key_judgements
    ):
        return True
    wanted = _content_words(question)
    if not wanted:
        return True
    return len(wanted & prose) / len(wanted) >= OVERLAP_THRESHOLD


def check_requirement_gate(
    body: ReportBody,
    direction: Direction | None,
    requirements: Sequence[IntelligenceRequirement] = (),
    existing: Sequence[Finding] = (),
) -> list[Finding]:
    """Name every requirement the report neither answers nor discloses as a gap."""
    rows = requirement_rows(direction, requirements)
    if not rows:
        return []
    already = {
        finding.location for finding in existing if finding.rule == REQUIREMENT_COVERAGE_RULE
    }
    disclosed = {gap.eei for gap in body.gaps if gap.eei}
    prose = _prose_words(body)
    return [
        Finding(
            REQUIREMENT_GATE_RULE,
            Severity.ERROR,
            requirement_id,
            f"{requirement_id} is not answered in the report and is not listed as a gap: "
            f"“{question}”.",
        )
        for requirement_id, question in rows
        if requirement_id not in already
        and requirement_id not in disclosed
        and not _answered(body, requirement_id, question, prose)
    ]
