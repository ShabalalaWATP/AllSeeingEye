"""Evidence provenance and minimum structure checks for report validation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace

from ase.domain.doctrine import sentences
from ase.domain.evidence import EvidenceItem
from ase.domain.reports import KeyJudgement, ReportBody, ReportingTheme
from ase.domain.validation_types import Finding, Severity

MAX_REPORT_CHARS = 60_000


def derive_reporting_grades(
    body: ReportBody, frozen: Mapping[str, EvidenceItem], findings: list[Finding]
) -> ReportBody:
    """Display each distinct cited grade unchanged, never a model-created aggregate."""
    themes: list[ReportingTheme] = []
    for theme in body.reporting:
        items = []
        for index, item in enumerate(theme.items):
            grades = ", ".join(dict.fromkeys(frozen[label].grade for label in item.evidence))
            if item.grade != grades:
                findings.append(
                    Finding(
                        "grade",
                        Severity.WARNING,
                        f"reporting.{theme.theme}[{index}]",
                        "Reporting grades replaced with the exact grades of cited frozen evidence.",
                    )
                )
            items.append(replace(item, grade=grades))
        themes.append(replace(theme, items=tuple(items)))
    return replace(body, reporting=tuple(themes))


def check_structure(body: ReportBody, findings: list[Finding]) -> None:
    for name in ("key_judgements", "reporting", "assessment", "sourcing_statement"):
        if not getattr(body, name):
            findings.append(Finding("structure", Severity.ERROR, name, f"{name} is required"))
    for name, values in (
        ("key_judgements", body.key_judgements),
        ("assumptions", body.assumptions),
    ):
        identifiers = [item.id for item in values]
        if len(identifiers) != len(set(identifiers)) or any(not id_.strip() for id_ in identifiers):
            findings.append(
                Finding(
                    "identifier", Severity.ERROR, name, "Identifiers must be nonempty and unique"
                )
            )
    for index, section in enumerate(body.assessment):
        if not section.text.strip() or not section.heading.strip() or not section.evidence:
            findings.append(
                Finding(
                    "evidence",
                    Severity.ERROR,
                    f"assessment[{index}]",
                    "Assessment sections need a heading, meaningful text and cited evidence",
                )
            )
    if body.key_judgements and not body.assumptions:
        findings.append(
            Finding(
                "assumption",
                Severity.ERROR,
                "assumptions",
                "Assumptions are required when there are key judgements",
            )
        )
    if len(body.key_judgements) >= 2 and not body.alternative_hypotheses:
        findings.append(
            Finding(
                "alternatives",
                Severity.ERROR,
                "alternative_hypotheses",
                "At least one alternative hypothesis is required with two or more judgements",
            )
        )
    if sum(len(text) for text in body.texts()) > MAX_REPORT_CHARS:
        findings.append(
            Finding("length", Severity.ERROR, "report", "The report exceeds the character budget")
        )


def check_judgement_support(
    judgement: KeyJudgement, assumption_ids: frozenset[str], out: list[Finding]
) -> None:
    """Require identifiable observed support and disambiguated judgement structure."""
    where = judgement.id
    if not judgement.supporting_evidence:
        out.append(
            Finding(
                "evidence",
                Severity.ERROR,
                where,
                "A judgement must cite supporting evidence; assumptions alone are not observations",
            )
        )
    if set(judgement.supporting_evidence) & set(judgement.contradicting_evidence):
        out.append(
            Finding(
                "citation",
                Severity.ERROR,
                where,
                "The same evidence cannot be both supporting and contradicting without review",
            )
        )
    if len(sentences(judgement.statement)) != 1:
        out.append(Finding("structure", Severity.ERROR, where, "A judgement must be one sentence"))
    unknown = [a for a in judgement.assumptions if a not in assumption_ids]
    if unknown:
        out.append(
            Finding(
                "assumption",
                Severity.ERROR,
                where,
                f"Unknown assumption id(s): {', '.join(unknown)}",
            )
        )
