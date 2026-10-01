"""Rebind a frozen source-assessment receipt to a copied report version.

Capture and claim identities are derived from the report version, so a copy cannot
reuse them. The assessment values, digests, reviews and origin decisions are kept;
only the identities are recomputed for the new version. A projection that cannot be
rebound exactly becomes an unavailable receipt, never a silently altered assessment.
"""

from collections.abc import Mapping, Sequence
from dataclasses import replace
from uuid import NAMESPACE_URL, UUID, uuid5

from ase.domain.evidence import EvidenceItem
from ase.domain.origin_chains import analyse_origin_chains
from ase.domain.reports import ReportBody
from ase.domain.source_assessment import ScopedSourceAssessment
from ase.domain.source_assessment_bindings import (
    SourceAssessmentTargets,
    assert_source_assessment_matches,
    prepare_source_assessment_targets,
)
from ase.domain.source_assessment_report import (
    ReportSourceAssessment,
    SourceAssessmentCapture,
)

UNBOUND_REASON = "The source assessment could not be rebound to this copied version."


def _node_id(capture_id: str, claim_id: str) -> str:
    return uuid5(NAMESPACE_URL, f"ase:source-node:{capture_id}:{claim_id}").hex


def _identity_map(
    projection: ReportSourceAssessment, targets: SourceAssessmentTargets
) -> dict[str, str]:
    """Old to new capture, claim and derived node identities, matched by label and digest."""
    new_evidence = {row.label: row for row in targets.evidence}
    new_claims = {row.judgement_id: row for row in targets.claims}
    ids: dict[str, str] = {}
    for old in projection.evidence:
        found = new_evidence[old.label]
        if found.digest != old.digest:
            raise ValueError("Copied evidence no longer matches its frozen digest.")
        ids[old.capture_id] = found.capture_id
    for old_claim in projection.claims:
        claim = new_claims[old_claim.judgement_id]
        if claim.digest != old_claim.digest:
            raise ValueError("Copied judgement no longer matches its frozen digest.")
        ids[old_claim.claim_id] = claim.claim_id
    if len(ids) != len(projection.evidence) + len(projection.claims):
        raise ValueError("Frozen capture and claim identities must be distinct.")
    for node in projection.origins.nodes:
        if node.id == _node_id(node.evidence_id, node.claim_id):
            ids[node.id] = _node_id(ids[node.evidence_id], ids[node.claim_id])
    return ids


def _swap(ids: Mapping[str, str], value: str | None) -> str | None:
    return None if value is None else ids.get(value, value)


def _assessment(row: ScopedSourceAssessment, ids: Mapping[str, str]) -> ScopedSourceAssessment:
    revision = row.assertion_revision
    authenticity = row.authenticity
    return replace(
        row,
        evidence_id=ids[row.evidence_id],
        claim_id=ids[row.claim_id],
        assertion_revision=(
            replace(
                revision, evidence_id=ids[revision.evidence_id], claim_id=ids[revision.claim_id]
            )
            if revision is not None
            else None
        ),
        authenticity=(
            replace(authenticity, evidence_id=ids[authenticity.evidence_id])
            if authenticity is not None
            else None
        ),
    )


def _rebound_projection(
    projection: ReportSourceAssessment,
    report_version_id: UUID,
    body: ReportBody,
    evidence: Sequence[EvidenceItem],
) -> ReportSourceAssessment:
    targets = prepare_source_assessment_targets(
        report_version_id,
        body,
        evidence,
        subjects={row.judgement_id: row.subject for row in projection.claims},
    )
    ids = _identity_map(projection, targets)
    origins = projection.origins
    nodes = [
        replace(
            node,
            id=ids.get(node.id, node.id),
            evidence_id=ids[node.evidence_id],
            claim_id=ids[node.claim_id],
        )
        for node in origins.nodes
    ]
    edges = [
        replace(
            row.edge,
            child_id=ids.get(row.edge.child_id, row.edge.child_id),
            parent_id=ids.get(row.edge.parent_id, row.edge.parent_id),
        )
        for row in origins.relationships
    ]
    observations = [
        replace(
            row,
            evidence_id=ids[row.evidence_id],
            target_evidence_id=_swap(ids, row.target_evidence_id),
            claim_id=_swap(ids, row.claim_id),
        )
        for row in origins.observations
    ]
    rebound = ReportSourceAssessment(
        report_version_id,
        projection.frozen_at,
        targets.evidence,
        targets.claims,
        tuple(_assessment(row, ids) for row in projection.assessments),
        analyse_origin_chains(nodes, edges, observations=observations),
        projection.schema_version,
        projection.policy_version,
    )
    assert_source_assessment_matches(
        rebound, report_version_id=report_version_id, body=body, evidence=evidence
    )
    return rebound


def rebind_source_assessment(
    capture: SourceAssessmentCapture,
    *,
    report_version_id: UUID,
    body: ReportBody,
    evidence: Sequence[EvidenceItem],
) -> tuple[SourceAssessmentCapture, bool]:
    """Return the rebound receipt and whether its captured assessment was preserved."""
    if capture.projection is None:
        return (
            SourceAssessmentCapture(
                report_version_id, capture.frozen_at, capture.status, reason=capture.reason
            ),
            True,
        )
    try:
        projection = _rebound_projection(capture.projection, report_version_id, body, evidence)
    except (ValueError, TypeError, KeyError, AttributeError):
        return (
            SourceAssessmentCapture(
                report_version_id, capture.frozen_at, "unavailable", reason=UNBOUND_REASON
            ),
            False,
        )
    return (
        SourceAssessmentCapture(report_version_id, capture.frozen_at, "captured", projection),
        True,
    )
