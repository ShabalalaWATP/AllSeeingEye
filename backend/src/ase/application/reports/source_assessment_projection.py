"""Projection from final report judgements and exact captured evidence.

Production can prepare targets after the last redraft, load authorised histories
for those exact scopes, build this projection and persist its JSON with the same
ReportVersion. This seam does not activate grading, confidence or publication
changes. It covers saved judgement boundaries, not newly extracted atomic claims.
"""

from collections.abc import Mapping, Sequence
from datetime import datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from ase.domain.evidence import EvidenceItem
from ase.domain.origin_chains import OriginAnalysis, analyse_origin_chains
from ase.domain.origin_records import OriginNode, OriginRole
from ase.domain.reports import ReportBody
from ase.domain.source_assessment import (
    AssertionRatingRevision,
    IssuerAuthenticity,
    SourceRatingRevision,
    assessment_time,
)
from ase.domain.source_assessment_bindings import (
    SourceAssessmentTargets,
    assert_source_assessment_matches,
    prepare_source_assessment_targets,
)
from ase.domain.source_assessment_policy import MAX_RATING_REVISIONS, resolve_source_assessment
from ase.domain.source_assessment_records import (
    source_assessment_report_from_dict,
    source_assessment_report_to_dict,
)
from ase.domain.source_assessment_report import (
    ReportSourceAssessment,
    SourceAssessmentCapture,
)

type SourceHistories = Mapping[tuple[str, str], tuple[SourceRatingRevision, ...]]
type AssertionHistories = Mapping[tuple[str, str], tuple[AssertionRatingRevision, ...]]

__all__ = [
    "AssertionHistories",
    "SourceAssessmentTargets",
    "SourceHistories",
    "build_source_assessment_projection",
    "capture_unassessed_report_sources",
    "prepare_source_assessment_targets",
    "restore_source_assessment_projection",
]


def capture_unassessed_report_sources(
    report_version_id: UUID,
    body: ReportBody,
    evidence: Sequence[EvidenceItem],
    *,
    frozen_at: datetime,
) -> SourceAssessmentCapture:
    """Capture the production baseline while no authorised scoped-review adapter exists.

    Explicit unassessed scope and F/6 describe missing reviews, without replacing
    historic evidence grades. Invalid draft citations retain an unavailable
    receipt so a reviewable report can still be saved after its paid generation.
    """
    try:
        targets = prepare_source_assessment_targets(
            report_version_id,
            body,
            evidence,
            subjects={row.id: "unassessed" for row in body.key_judgements},
        )
        projection = build_source_assessment_projection(targets, frozen_at=frozen_at)
    except (ValueError, TypeError):
        return SourceAssessmentCapture(
            report_version_id,
            frozen_at,
            "unavailable",
            reason="The final draft could not be bound to a complete scoped source assessment.",
        )
    return SourceAssessmentCapture(report_version_id, frozen_at, "captured", projection)


def _check_histories[Revision: SourceRatingRevision | AssertionRatingRevision](
    histories: Mapping[tuple[str, str], tuple[Revision, ...]],
    expected: set[tuple[str, str]],
    kind: type[Revision],
    frozen_at: datetime,
) -> None:
    if not histories.keys() <= expected:
        raise ValueError("Rating history keys must match requested report scopes.")
    for key, history in histories.items():
        if type(history) is not tuple or len(history) > MAX_RATING_REVISIONS:
            raise ValueError("Rating histories must retain their bounded immutable revisions.")
        for row in history:
            if not isinstance(row, kind):
                raise ValueError("Invalid typed rating history.")
            scope = (
                (row.source_id, row.subject)
                if isinstance(row, SourceRatingRevision)
                else (row.evidence_id, row.claim_id)
            )
            if scope != key or row.review.recorded_at > frozen_at:
                raise ValueError("Rating history crosses the requested scope or freeze date.")


def _unknown_origins(targets: SourceAssessmentTargets) -> OriginAnalysis:
    evidence = {row.capture_id: row for row in targets.evidence}
    return analyse_origin_chains(
        [
            OriginNode(
                uuid5(NAMESPACE_URL, f"ase:source-node:{use.capture_id}:{claim.claim_id}").hex,
                use.capture_id,
                claim.claim_id,
                evidence[use.capture_id].source_id,
                OriginRole.UNKNOWN,
                evidence[use.capture_id].declared_organisation,
            )
            for claim in targets.claims
            for use in claim.uses
        ]
    )


def build_source_assessment_projection(
    targets: SourceAssessmentTargets,
    *,
    frozen_at: datetime,
    source_histories: SourceHistories | None = None,
    assertion_histories: AssertionHistories | None = None,
    authenticities: Mapping[str, IssuerAuthenticity] | None = None,
    origins: OriginAnalysis | None = None,
) -> ReportSourceAssessment:
    """Resolve only supplied, authorised scoped histories; missing grades remain F/6.

    Historic event grades are not silently adopted or overwritten. An adapter
    retaining inherited grades must supply explicit LEGACY revisions and policy
    notes. Model suggestions may reference trusted origin observations, never
    populate the observation registry or authenticated reviewer fields themselves.
    Supplied original identities/roles also require a trusted origin adapter;
    frozen organisation declarations cannot be changed through this projection.
    """
    assessment_time(frozen_at)
    source_histories = {} if source_histories is None else source_histories
    assertion_histories = {} if assertion_histories is None else assertion_histories
    authenticities = {} if authenticities is None else authenticities
    if not all(
        isinstance(values, Mapping)
        for values in (source_histories, assertion_histories, authenticities)
    ):
        raise ValueError("Scoped source assessment inputs require explicit mappings.")
    evidence = {row.capture_id: row for row in targets.evidence}
    source_scopes = {
        (evidence[use.capture_id].source_id, claim.subject)
        for claim in targets.claims
        for use in claim.uses
    }
    assertion_scopes = {
        (use.capture_id, claim.claim_id) for claim in targets.claims for use in claim.uses
    }
    _check_histories(source_histories, source_scopes, SourceRatingRevision, frozen_at)
    _check_histories(assertion_histories, assertion_scopes, AssertionRatingRevision, frozen_at)
    if not authenticities.keys() <= {key[0] for key in assertion_scopes}:
        raise ValueError("Issuer authenticity must address captured, cited report evidence.")
    assessments = tuple(
        resolve_source_assessment(
            evidence_id=use.capture_id,
            claim_id=claim.claim_id,
            source_id=evidence[use.capture_id].source_id,
            subject=claim.subject,
            source_history=source_histories.get(
                (evidence[use.capture_id].source_id, claim.subject), ()
            ),
            assertion_history=assertion_histories.get((use.capture_id, claim.claim_id), ()),
            authenticity=authenticities.get(use.capture_id),
        )
        for claim in targets.claims
        for use in claim.uses
    )
    report = ReportSourceAssessment(
        targets.report_version_id,
        frozen_at,
        targets.evidence,
        targets.claims,
        assessments,
        origins or _unknown_origins(targets),
    )
    source_assessment_report_to_dict(report)
    return report


def restore_source_assessment_projection(
    data: object,
    *,
    report_version_id: UUID,
    body: ReportBody,
    evidence: Sequence[EvidenceItem],
    required: bool = False,
) -> ReportSourceAssessment | None:
    """Read the saved exact-version projection without consulting current source ratings.

    Changed text, capture content, citations or version identity invalidates reuse.
    The original frozen subject choices remain unchanged by current brief edits.
    """
    report = source_assessment_report_from_dict(data, required=required)
    if report is None:
        return None
    assert_source_assessment_matches(
        report, report_version_id=report_version_id, body=body, evidence=evidence
    )
    return report
