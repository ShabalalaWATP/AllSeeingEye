"""The report linter (docs/03 section 11): what can be checked mechanically, is."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from enum import StrEnum

from ase.domain.doctrine import (
    Confidence,
    distinct_bands,
    find_hedges,
    find_urls,
    mentions_confidence,
    opens_as_judgement,
    scan_likelihood,
    sentences,
)
from ase.domain.reports import (
    MAX_JUDGEMENT_CHARS,
    AlternativeHypothesis,
    AssessmentSection,
    KeyJudgement,
    ReportBody,
    ReportingItem,
    ReportingTheme,
)

MAX_REPORT_CHARS = 60_000
CONFIDENCE_ORDER = {Confidence.LOW: 0, Confidence.MODERATE: 1, Confidence.HIGH: 2}


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class Finding:
    rule: str
    severity: Severity
    location: str
    message: str


@dataclass(frozen=True, slots=True)
class ValidationResult:
    body: ReportBody
    findings: tuple[Finding, ...]

    @property
    def errors(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.severity is Severity.ERROR)

    @property
    def passed(self) -> bool:
        return not self.errors


def _strip(
    labels: Sequence[str], known: frozenset[str], where: str, out: list[Finding]
) -> tuple[str, ...]:
    kept = tuple(label for label in labels if label in known)
    for label in labels:
        if label not in known:
            out.append(
                Finding("citation", Severity.WARNING, where, f"Unknown evidence {label} removed")
            )
    return kept


def _strip_unknown_citations(
    body: ReportBody, known: frozenset[str], out: list[Finding]
) -> ReportBody:
    judgements = tuple(
        replace(
            j,
            supporting_evidence=_strip(j.supporting_evidence, known, j.id, out),
            contradicting_evidence=_strip(j.contradicting_evidence, known, j.id, out),
        )
        for j in body.key_judgements
    )
    reporting = tuple(
        ReportingTheme(
            theme=theme.theme,
            items=tuple(
                ReportingItem(
                    item.text,
                    _strip(item.evidence, known, f"reporting.{theme.theme}", out),
                    item.grade,
                )
                for item in theme.items
            ),
        )
        for theme in body.reporting
    )
    assessment = tuple(
        AssessmentSection(
            s.heading, s.text, _strip(s.evidence, known, f"assessment.{s.heading}", out)
        )
        for s in body.assessment
    )
    alternatives = tuple(
        AlternativeHypothesis(
            a.text, a.why_less_likely, _strip(a.evidence, known, "alternatives", out)
        )
        for a in body.alternative_hypotheses
    )
    return replace(
        body,
        key_judgements=judgements,
        reporting=reporting,
        assessment=assessment,
        alternative_hypotheses=alternatives,
    )


def _check_judgement(
    judgement: KeyJudgement, assumption_ids: frozenset[str], out: list[Finding]
) -> KeyJudgement:
    where = judgement.id
    scan = scan_likelihood(judgement.statement)
    bands = distinct_bands(judgement.statement)
    if scan.forbidden:
        out.append(
            Finding(
                "yardstick",
                Severity.ERROR,
                where,
                f"Forbidden likelihood language: {', '.join(scan.forbidden)}",
            )
        )
    if len(bands) != 1:
        out.append(
            Finding(
                "yardstick",
                Severity.ERROR,
                where,
                f"A judgement needs exactly one yardstick term, found {len(bands)}",
            )
        )
    elif bands[0] is not judgement.probability:
        out.append(
            Finding(
                "yardstick",
                Severity.ERROR,
                where,
                f"The statement says {bands[0].value} "
                f"but probability is {judgement.probability.value}",
            )
        )
    hedges = find_hedges(judgement.statement)
    if hedges:
        out.append(
            Finding(
                "hedge", Severity.ERROR, where, f"Hedge words in a judgement: {', '.join(hedges)}"
            )
        )
    if not judgement.confidence_statement.strip():
        out.append(
            Finding("confidence", Severity.ERROR, where, "A judgement needs a confidence statement")
        )
    for sentence in sentences(judgement.statement) + sentences(judgement.confidence_statement):
        if mentions_confidence(sentence) and scan_likelihood(sentence).bands:
            out.append(
                Finding(
                    "confidence",
                    Severity.ERROR,
                    where,
                    "A sentence mixes a yardstick term with a confidence word",
                )
            )
            break
    if not opens_as_judgement(judgement.statement):
        out.append(
            Finding(
                "style", Severity.WARNING, where, 'Judgements open with "We assess" or "We judge"'
            )
        )
    if len(judgement.statement) >= MAX_JUDGEMENT_CHARS:
        out.append(
            Finding("length", Severity.WARNING, where, "Judgement statement is at the length limit")
        )
    if not judgement.supporting_evidence and not judgement.assumptions:
        out.append(
            Finding(
                "evidence", Severity.ERROR, where, "A judgement must cite evidence or an assumption"
            )
        )
    unknown = [a for a in judgement.assumptions if a not in assumption_ids]
    if unknown:
        out.append(
            Finding(
                "assumption",
                Severity.WARNING,
                where,
                f"Unknown assumption id(s): {', '.join(unknown)}",
            )
        )
    return judgement


def validate_body(
    body: ReportBody,
    evidence_labels: frozenset[str],
    evidence_urls: Mapping[str, str | None],
    *,
    confidence_ceiling: Confidence = Confidence.HIGH,
    previous_exists: bool = False,
) -> ValidationResult:
    """Apply every rule; return the cleaned body and the findings, errors first."""
    findings: list[Finding] = []
    body = _strip_unknown_citations(body, evidence_labels, findings)
    assumption_ids = frozenset(a.id for a in body.assumptions)
    judgements: list[KeyJudgement] = []
    for judgement in body.key_judgements:
        checked = _check_judgement(judgement, assumption_ids, findings)
        if CONFIDENCE_ORDER[checked.confidence] > CONFIDENCE_ORDER[confidence_ceiling]:
            findings.append(
                Finding(
                    "confidence_ceiling",
                    Severity.WARNING,
                    checked.id,
                    f"Confidence lowered to {confidence_ceiling.value}: "
                    "the information base does not support more",
                )
            )
            checked = replace(checked, confidence=confidence_ceiling)
        if previous_exists and checked.change_from_previous is None:
            findings.append(
                Finding(
                    "change",
                    Severity.ERROR,
                    checked.id,
                    "change_from_previous is required when a previous version exists",
                )
            )
        judgements.append(checked)
    body = replace(body, key_judgements=tuple(judgements))
    _check_reporting(body, findings)
    _check_prose(body, evidence_urls, findings)
    _check_structure(body, findings)
    findings.sort(key=lambda f: (0 if f.severity is Severity.ERROR else 1, f.rule))
    return ValidationResult(body=body, findings=tuple(findings))


def _check_reporting(body: ReportBody, findings: list[Finding]) -> None:
    for theme in body.reporting:
        for index, item in enumerate(theme.items):
            where = f"reporting.{theme.theme}[{index}]"
            if scan_likelihood(item.text).bands:
                findings.append(
                    Finding(
                        "yardstick",
                        Severity.ERROR,
                        where,
                        "Reporting must not contain yardstick terms",
                    )
                )
            if not item.evidence:
                findings.append(
                    Finding("evidence", Severity.ERROR, where, "Reporting items must cite evidence")
                )


def _check_prose(
    body: ReportBody, evidence_urls: Mapping[str, str | None], findings: list[Finding]
) -> None:
    cited = body.cited_labels()
    allowed = {url for label, url in evidence_urls.items() if url and label in cited}
    for text in body.texts():
        for url in find_urls(text):
            if url.rstrip(".,") not in allowed:
                findings.append(
                    Finding(
                        "url", Severity.ERROR, "text", f"URL not from cited evidence: {url[:80]}"
                    )
                )
    hedged = [text for text in body.texts() if find_hedges(text)]
    if hedged:
        findings.append(
            Finding(
                "hedge",
                Severity.WARNING,
                "text",
                f"{len(hedged)} passage(s) use hedge words; "
                "check they describe capability, not likelihood",
            )
        )


def _check_structure(body: ReportBody, findings: list[Finding]) -> None:
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
