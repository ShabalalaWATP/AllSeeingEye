"""House style and template structure over a drafted report, mechanically and visibly.

No model is called and no text is changed. Each violation becomes a review reason that
names what was written, where, and what the template or the house style expects.
"""

from __future__ import annotations

from ase.application.reports.numeric_checks import prose_passages
from ase.domain.house_style import MAX_STYLE_REPORTS, style_violations
from ase.domain.report_quality_rules import HOUSE_STYLE_RULE, TEMPLATE_STRUCTURE_RULE
from ase.domain.report_structure import PART_LABELS, ExpectedHeading, structure_for
from ase.domain.reports import ReportBody
from ase.domain.validation_types import Finding, Severity


def _error(rule: str, location: str, message: str) -> Finding:
    return Finding(rule, Severity.ERROR, location, message)


def _present(body: ReportBody, part: str) -> bool:
    if part == "indicators_and_warning":
        return bool(body.indicators_and_warning.changes)
    return bool(getattr(body, part, None))


def _written_headings(body: ReportBody) -> tuple[str, ...]:
    return (
        *(theme.theme for theme in body.reporting),
        *(section.heading for section in body.assessment),
    )


def _heading_position(headings: tuple[str, ...], expected: ExpectedHeading) -> int | None:
    return next(
        (
            index
            for index, heading in enumerate(headings)
            if expected.key in " ".join(heading.split()).casefold()
        ),
        None,
    )


def check_headings(body: ReportBody, template_id: str) -> list[Finding]:
    """Required headings must be present, filled in and in the template's order."""
    structure = structure_for(template_id)
    written = _written_headings(body)
    findings: list[Finding] = []
    if any(not heading.strip() for heading in written):
        findings.append(
            _error(
                TEMPLATE_STRUCTURE_RULE,
                "headings",
                "A reporting theme or assessment section was written without a heading, "
                "so the reader cannot tell what it covers.",
            )
        )
    found: list[tuple[int, ExpectedHeading]] = []
    for expected in structure.expected_headings:
        position = _heading_position(written, expected)
        if position is None:
            findings.append(
                _error(
                    TEMPLATE_STRUCTURE_RULE,
                    "headings",
                    f"The {template_id} template asks for a “{expected.label}” "
                    "section and the report does not have one.",
                )
            )
        else:
            found.append((position, expected))
    ordered = [row[1].label for row in found]
    if ordered != [row[1].label for row in sorted(found, key=lambda row: row[0])]:
        findings.append(
            _error(
                TEMPLATE_STRUCTURE_RULE,
                "headings",
                "The report's sections are not in the order the "
                f"{template_id} template sets out: {', '.join(ordered)}.",
            )
        )
    return findings


def check_structure(body: ReportBody, template_id: str) -> list[Finding]:
    """Required parts, judgement counts and the length the template expects."""
    structure = structure_for(template_id)
    findings = [
        _error(
            TEMPLATE_STRUCTURE_RULE,
            part,
            f"The {template_id} template requires {PART_LABELS.get(part, part)} "
            "and the report does not have it.",
        )
        for part in structure.required_parts
        if not _present(body, part)
    ]
    count = len(body.key_judgements)
    if body.key_judgements and not structure.min_judgements <= count <= structure.max_judgements:
        findings.append(
            _error(
                TEMPLATE_STRUCTURE_RULE,
                "key_judgements",
                f"The {template_id} template expects between {structure.min_judgements} and "
                f"{structure.max_judgements} key judgements; the report has {count}.",
            )
        )
    length = sum(len(text) for text in body.texts())
    if length > structure.max_chars:
        findings.append(
            _error(
                TEMPLATE_STRUCTURE_RULE,
                "report",
                f"The report runs to {length:,} characters, beyond the "
                f"{structure.max_chars:,} the {template_id} template allows.",
            )
        )
    elif body.key_judgements and length < structure.min_chars:
        findings.append(
            _error(
                TEMPLATE_STRUCTURE_RULE,
                "report",
                f"The report runs to only {length:,} characters, below the "
                f"{structure.min_chars:,} the {template_id} template expects.",
            )
        )
    return findings + check_headings(body, template_id)


def _style_passages(body: ReportBody) -> list[tuple[str, str]]:
    """Style applies to every written field, including the two the engine co-authors."""
    return [
        *prose_passages(body),
        *((row.id, row.confidence_statement) for row in body.key_judgements),
        ("sourcing_statement", body.sourcing_statement),
    ]


def check_house_style(body: ReportBody) -> list[Finding]:
    """UK spelling, dash use, plain-text fields and citation placement, named in full."""
    findings: list[Finding] = []
    seen: set[tuple[str, str]] = set()
    for location, text in _style_passages(body):
        for violation in style_violations(text):
            key = (violation.kind, violation.found.casefold())
            if key in seen:
                continue
            seen.add(key)
            findings.append(_error(HOUSE_STYLE_RULE, location, violation.explanation))
    if len(findings) > MAX_STYLE_REPORTS:
        remaining = len(findings) - MAX_STYLE_REPORTS
        findings = [
            *findings[:MAX_STYLE_REPORTS],
            _error(
                HOUSE_STYLE_RULE,
                "report",
                f"A further {remaining} house-style problem(s) were found; the prose needs "
                "an editorial pass.",
            ),
        ]
    return findings
