"""The report linter (docs/03 section 11): what can be checked mechanically, is."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace

from ase.domain.claim_passage_validation import (
    ClaimPassageCitation,
    FrozenClaimPassage,
    check_claim_passages,
)
from ase.domain.confidence_rationale import generic_confidence_rationale
from ase.domain.doctrine import (
    Confidence,
    find_hedges,
    has_numeric_likelihood,
    mentions_confidence,
    opens_as_judgement,
    scan_likelihood,
    sentences,
)
from ase.domain.evidence import EvidenceItem, quality_of_information
from ase.domain.judgement_assessment import assess_judgement
from ase.domain.report_prose_validation import check_prose
from ase.domain.report_support import (
    check_judgement_support,
    check_structure,
    derive_reporting_grades,
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
from ase.domain.validation_types import Finding, Severity, ValidationResult

__all__ = ["Finding", "Severity", "ValidationResult", "validate_body"]

CONFIDENCE_ORDER = {Confidence.LOW: 0, Confidence.MODERATE: 1, Confidence.HIGH: 2}


def _strip(
    labels: Sequence[str], known: frozenset[str], where: str, out: list[Finding]
) -> tuple[str, ...]:
    kept = tuple(label for label in labels if label in known)
    for label in labels:
        if label not in known:
            out.append(
                Finding("citation", Severity.ERROR, where, f"Unknown evidence {label} removed")
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
    bands = scan.bands
    if scan.forbidden:
        out.append(
            Finding(
                "yardstick",
                Severity.ERROR,
                where,
                f"Forbidden likelihood language: {', '.join(scan.forbidden)}",
            )
        )
    if has_numeric_likelihood(judgement.statement):
        out.append(
            Finding(
                "yardstick",
                Severity.ERROR,
                where,
                "Judgements use the qualitative yardstick, not numeric chance estimates",
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
    rationale = judgement.confidence_statement.strip()
    if generic_confidence_rationale(rationale):
        out.append(
            Finding(
                "confidence",
                Severity.ERROR,
                where,
                "A judgement needs a specific confidence rationale tied to its information base, "
                "analytical rigour or volatility",
            )
        )
    rationale_scan = scan_likelihood(rationale)
    if rationale_scan.bands or rationale_scan.forbidden or has_numeric_likelihood(rationale):
        out.append(
            Finding(
                "yardstick",
                Severity.ERROR,
                where,
                "Confidence rationale must describe evidence and method, not likelihood",
            )
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
    check_judgement_support(judgement, assumption_ids, out)
    return judgement


def validate_body(
    body: ReportBody,
    evidence_labels: frozenset[str],
    evidence_urls: Mapping[str, str | None],
    *,
    confidence_ceiling: Confidence = Confidence.HIGH,
    previous_exists: bool = False,
    evidence_items: Sequence[EvidenceItem] | None = None,
    original_passages: Mapping[str, FrozenClaimPassage] | None = None,
    passage_citations: Mapping[str, Sequence[ClaimPassageCitation]] | None = None,
) -> ValidationResult:
    """Apply every rule; return the cleaned body and the findings, errors first."""
    if (original_passages is None) != (passage_citations is None):
        raise ValueError("Frozen passages and their exact citation links must be supplied together")
    findings: list[Finding] = []
    frozen = {item.label: item for item in evidence_items} if evidence_items is not None else None
    if frozen is not None:
        evidence_labels = frozenset(frozen)
        evidence_urls = {label: item.url for label, item in frozen.items()}
    body = _strip_unknown_citations(body, evidence_labels, findings)
    assumption_ids = frozenset(a.id for a in body.assumptions)
    judgements: list[KeyJudgement] = []
    for judgement in body.key_judgements:
        checked = _check_judgement(judgement, assumption_ids, findings)
        if original_passages is not None and passage_citations is not None:
            links = passage_citations.get(checked.id)
            if links is not None:
                findings.extend(
                    check_claim_passages(
                        checked.id,
                        checked.statement,
                        links,
                        original_passages,
                        evidence_labels,
                    )
                )
        ceiling = confidence_ceiling
        if frozen is not None:
            support_assessment = assess_judgement(checked, tuple(frozen.values()))
            cited_ceiling = support_assessment.confidence_ceiling
            ceiling = min(ceiling, cited_ceiling, key=CONFIDENCE_ORDER.__getitem__)
        if CONFIDENCE_ORDER[checked.confidence] > CONFIDENCE_ORDER[ceiling]:
            findings.append(
                Finding(
                    "confidence_ceiling",
                    Severity.WARNING,
                    checked.id,
                    f"Confidence lowered to {ceiling.value}: "
                    "the cited supporting evidence does not support more",
                )
            )
            checked = replace(
                checked,
                confidence=ceiling,
                confidence_statement=(
                    f"Engine confidence ceiling: {ceiling.value}, based on cited support. "
                    f"Model rationale (unverified): {checked.confidence_statement}"
                ),
            )
        if frozen is not None:
            groups = sum(group.known_organisation for group in support_assessment.support_groups)
            checked = replace(
                checked,
                confidence_statement=(
                    f"Engine confidence ceiling: {ceiling.value}. Cited support: "
                    f"{len(support_assessment.supporting_labels)} item(s), "
                    f"{groups} "
                    "declared organisation group(s); independent sourcing not verified. "
                    f"Support {support_assessment.support_tier.value}; "
                    f"opposition {support_assessment.opposition_tier.value}. "
                    "Relationships are model-assigned. "
                    f"Model rationale (unverified): {judgement.confidence_statement}"
                ),
            )
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
    if passage_citations is not None:
        for unknown in sorted(set(passage_citations) - {item.id for item in judgements}):
            findings.append(
                Finding("citation", Severity.ERROR, unknown, "Passage links name no judgement")
            )
    body = replace(body, key_judgements=tuple(judgements))
    if frozen is not None:
        body = derive_reporting_grades(body, frozen, findings)
        cited = [frozen[label] for label in body.cited_labels()]
        body = replace(
            body,
            sourcing_statement=(
                "Cited evidence: "
                + quality_of_information(cited).describe()
                + " Frozen feed metadata and snippets; "
                "full source content has not been independently verified."
            ),
        )
    _check_reporting(body, findings)
    check_prose(body, evidence_urls, findings)
    check_structure(body, findings)
    findings.sort(key=lambda f: (0 if f.severity is Severity.ERROR else 1, f.rule))
    return ValidationResult(body=body, findings=tuple(findings))


def _check_reporting(body: ReportBody, findings: list[Finding]) -> None:
    for theme in body.reporting:
        for index, item in enumerate(theme.items):
            where = f"reporting.{theme.theme}[{index}]"
            reporting_scan = scan_likelihood(item.text)
            if (
                reporting_scan.bands
                or reporting_scan.forbidden
                or has_numeric_likelihood(item.text)
            ):
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
