"""Pure, opt-in checks of every judgement's frozen citations; no retrieval or report mutation."""

from collections.abc import Sequence

from ase.domain.citation_checks import (
    LIMITATIONS,
    MAX_CLAIM_CHARS,
    MAX_EXCERPT_CHARS,
    MAX_SOURCE_CHARS,
    METHOD_VERSION,
    CitationCheck,
    CitationStatus,
    ExcerptProposal,
    JudgementCitationCheck,
    Relation,
    ReportCitationChecks,
    SourceField,
    context_reasons,
    exact_excerpt,
    mismatch_indicators,
    select_excerpt,
)
from ase.domain.evidence import EvidenceItem
from ase.domain.reports import ReportBody

MAX_JUDGEMENTS = 20
MAX_EVIDENCE = 100
MAX_CITATIONS = 40


def _check(
    claim: str,
    label: str,
    relation: Relation,
    item: EvidenceItem | None,
    proposal: ExcerptProposal | None,
) -> CitationCheck:
    if item is None:
        return CitationCheck(
            label,
            relation,
            CitationStatus.ABSENT,
            None,
            None,
            None,
            (),
            ("The cited label is absent from frozen evidence.",),
        )
    field: SourceField = proposal.field if proposal else ("summary" if item.summary else "title")
    text = (item.summary if field == "summary" else item.title) or ""
    excerpt = (
        exact_excerpt(field, text, proposal.text)
        if proposal
        else select_excerpt(claim, field, text)
    )
    if excerpt is None:
        reason = (
            "The proposed excerpt is not present verbatim in the requested original field."
            if proposal
            else "No bounded original excerpt is available."
        )
        status = (
            CitationStatus.CONTEXT_INSUFFICIENT if text and not proposal else CitationStatus.ABSENT
        )
        return CitationCheck(
            label, relation, status, item.event_id, item.content_hash, None, (), (reason,)
        )
    reasons = context_reasons(claim, excerpt, item.language)
    # Mismatch cues are meaningful only within the supported language and a related passage.
    indicators = mismatch_indicators(claim, excerpt.text) if not reasons else ()
    status = (
        CitationStatus.CONTEXT_INSUFFICIENT
        if reasons
        else CitationStatus.REVIEW_REQUIRED
        if indicators
        else CitationStatus.EXCERPT_PRESENT
    )
    return CitationCheck(
        label,
        relation,
        status,
        item.event_id,
        item.content_hash,
        excerpt,
        indicators,
        reasons or ("The excerpt is present verbatim; semantic support remains unverified.",),
    )


def _validate(
    body: ReportBody, evidence: Sequence[EvidenceItem], proposals: Sequence[ExcerptProposal]
) -> None:
    if len(body.key_judgements) > MAX_JUDGEMENTS or len(evidence) > MAX_EVIDENCE:
        raise ValueError("The citation-check input exceeds its item limit")
    if len({row.id for row in body.key_judgements}) != len(body.key_judgements):
        raise ValueError("Judgement identifiers must be unique for excerpt requests")
    if len({row.label for row in evidence}) != len(evidence):
        raise ValueError("Frozen evidence labels must be unique")
    valid: set[tuple[str, str, str]] = set()
    for row in body.key_judgements:
        if (
            len(row.statement) > MAX_CLAIM_CHARS
            or len(row.supporting_evidence) + len(row.contradicting_evidence) > MAX_CITATIONS
        ):
            raise ValueError("A judgement exceeds the citation-check size limit")
        valid.update(
            (row.id, label, relation)
            for relation, labels in (
                ("supporting", row.supporting_evidence),
                ("contradicting", row.contradicting_evidence),
            )
            for label in labels
        )
    for item in evidence:
        if len(item.title) > MAX_SOURCE_CHARS or len(item.summary or "") > MAX_SOURCE_CHARS:
            raise ValueError("A frozen source exceeds the citation-check text limit")
    seen = set()
    for proposal in proposals:
        key = (proposal.judgement_id, proposal.label, proposal.relation)
        if key not in valid or key in seen:
            raise ValueError("The excerpt target is unknown or duplicated")
        if (
            proposal.field not in ("title", "summary")
            or not proposal.text.strip()
            or len(proposal.text) > MAX_EXCERPT_CHARS
        ):
            raise ValueError("The proposed original excerpt is invalid or exceeds its size limit")
        seen.add(key)


def check_report_citations(
    body: ReportBody,
    evidence: Sequence[EvidenceItem],
    proposed_excerpts: Sequence[ExcerptProposal] = (),
) -> ReportCitationChecks:
    """Check every judgement, retaining absences and advisory mismatches without grading."""
    _validate(body, evidence, proposed_excerpts)
    frozen = {item.label: item for item in evidence}
    proposals = {(row.judgement_id, row.label, row.relation): row for row in proposed_excerpts}
    rows = []
    for judgement in body.key_judgements:
        checks = []
        relations: tuple[tuple[Relation, tuple[str, ...]], ...] = (
            ("supporting", judgement.supporting_evidence),
            ("contradicting", judgement.contradicting_evidence),
        )
        for relation, labels in relations:
            for label in dict.fromkeys(labels):
                checks.append(
                    _check(
                        judgement.statement,
                        label,
                        relation,
                        frozen.get(label),
                        proposals.get((judgement.id, label, relation)),
                    )
                )
        reasons = (
            ()
            if judgement.supporting_evidence
            else ("No supporting citations were assigned to this judgement.",)
        )
        status = (
            CitationStatus.ABSENT
            if reasons
            else next(
                (
                    status
                    for status in (
                        CitationStatus.ABSENT,
                        CitationStatus.CONTEXT_INSUFFICIENT,
                        CitationStatus.REVIEW_REQUIRED,
                    )
                    if any(row.status is status for row in checks)
                ),
                CitationStatus.EXCERPT_PRESENT,
            )
        )
        rows.append(JudgementCitationCheck(judgement.id, status, tuple(checks), reasons))
    return ReportCitationChecks(METHOD_VERSION, tuple(rows), LIMITATIONS)


def check_generated_report_citations(
    body: ReportBody, evidence: Sequence[EvidenceItem]
) -> ReportCitationChecks:
    """Keep an invalid draft exportable while making unavailable checks explicit."""
    try:
        return check_report_citations(body, evidence)
    except ValueError as error:
        reason = f"Literal checks unavailable: {error}."
        return ReportCitationChecks(
            METHOD_VERSION,
            tuple(
                JudgementCitationCheck(
                    judgement.id,
                    CitationStatus.CONTEXT_INSUFFICIENT,
                    (),
                    (reason,),
                )
                for judgement in body.key_judgements
            ),
            (*LIMITATIONS, reason),
        )
