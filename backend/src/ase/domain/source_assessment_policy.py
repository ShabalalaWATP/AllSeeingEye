"""One explicit source/item policy seam, without regrading existing evidence.

Feed, research and retained-context adapters can supply these same scoped
histories. Historical applied revisions retain their original policy and grade.
This module does not alter the existing evidence contribution/confidence matrix.
"""

import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from ase.domain.events import Credibility, Reliability
from ase.domain.origin_chains import OriginAnalysis
from ase.domain.origin_records import AssessedOriginEdge, OriginGroup, OriginNode, OriginObservation
from ase.domain.source_assessment import (
    ASSESSMENT_POLICY_VERSION,
    AssertionRatingRevision,
    Assessor,
    IssuerAuthenticity,
    RatingStatus,
    ScopedSourceAssessment,
    SourceRatingRevision,
    assessment_text,
    assessment_time,
)

MAX_RATING_REVISIONS = 256


def _scope(row: SourceRatingRevision | AssertionRatingRevision) -> tuple[str, str]:
    if isinstance(row, SourceRatingRevision):
        return row.source_id, row.subject
    return row.evidence_id, row.claim_id


def append_rating_revision[Revision: SourceRatingRevision | AssertionRatingRevision](
    history: tuple[Revision, ...], revision: Revision
) -> tuple[Revision, ...]:
    """Append one scoped decision/proposal; automated inputs cannot replace human grades.

    Supersedes links form a review-history chain, including proposals. A later
    applied reviewer revision explicitly accepts or replaces earlier proposals.
    """
    candidate: tuple[Revision, ...] = (*history, revision)
    if type(history) is not tuple or len(candidate) > MAX_RATING_REVISIONS:
        raise ValueError("Rating history requires a bounded immutable sequence.")
    previous = None
    applied_reviewer = False
    ids: set[str] = set()
    for row in candidate:
        if type(row) is not type(revision) or _scope(row) != _scope(revision):
            raise ValueError("Rating history must retain one source/subject or evidence/claim.")
        review = row.review
        if review.id in ids or review.supersedes != (previous.id if previous else None):
            raise ValueError("Rating revisions require unique, consecutive history links.")
        if previous is not None:
            if review.recorded_at < previous.recorded_at:
                raise ValueError("Rating history dates must be ordered.")
            if review.policy_version != previous.policy_version and review.policy_note is None:
                raise ValueError("A policy change requires an explicit review note.")
        if review.status is RatingStatus.APPLIED:
            if applied_reviewer and review.assessor is not Assessor.REVIEWER:
                raise ValueError("An automated policy cannot overwrite a reviewer decision.")
            applied_reviewer = review.assessor is Assessor.REVIEWER
        ids.add(review.id)
        previous = review
    return candidate


def _current[Revision: SourceRatingRevision | AssertionRatingRevision](
    history: tuple[Revision, ...],
) -> Revision | None:
    if not history:
        return None
    append_rating_revision(history[:-1], history[-1])
    return next(
        (row for row in reversed(history) if row.review.status is RatingStatus.APPLIED), None
    )


def _policy_notes(
    source: SourceRatingRevision | None, assertion: AssertionRatingRevision | None
) -> list[str]:
    rows: tuple[SourceRatingRevision | AssertionRatingRevision | None, ...] = (source, assertion)
    notes = []
    for row in rows:
        if row is None:
            continue
        if row.review.policy_version != ASSESSMENT_POLICY_VERSION:
            notes.append("An inherited grade retains its applied policy; a current review is due.")
        if row.review.policy_note is not None:
            notes.append(row.review.policy_note)
    return notes


def resolve_source_assessment(
    *,
    evidence_id: str,
    claim_id: str,
    source_id: str,
    subject: str,
    source_history: tuple[SourceRatingRevision, ...] = (),
    assertion_history: tuple[AssertionRatingRevision, ...] = (),
    authenticity: IssuerAuthenticity | None = None,
) -> ScopedSourceAssessment:
    """Use applicable recorded grades, otherwise F/6; identity alone has no truth weight.

    No country, platform, article count or government flag assigns a grade. Scope
    keys are exact declared identifiers, not inferred subject similarity.
    """
    for value in (evidence_id, claim_id, source_id, subject):
        assessment_text(value, 200)
    source = _current(source_history)
    assertion = _current(assertion_history)
    if source is not None and _scope(source) != (source_id, subject):
        source = None
    if assertion is not None and _scope(assertion) != (evidence_id, claim_id):
        assertion = None
    if authenticity is not None and (
        authenticity.evidence_id != evidence_id or authenticity.issuer_id != source_id
    ):
        raise ValueError("Authenticity must describe this evidence and issuer.")
    notes = []
    if source is None:
        notes.append("No applied source-competence assessment matches this subject; retain F.")
    if assertion is None:
        notes.append("No applied assertion assessment matches this captured claim; retain 6.")
    notes.extend(_policy_notes(source, assertion))
    if (
        source is not None
        and source.expertise_basis is None
        and source.reliability is not Reliability.F
    ):
        notes.append(
            "Inherited source competence is undocumented; the preserved grade requires review."
        )
    if any(
        history and history[-1].review.status is RatingStatus.PROPOSAL
        for history in (source_history, assertion_history)
    ):
        notes.append("Unapplied rating proposals remain in review history; applied grades stand.")
    return ScopedSourceAssessment(
        evidence_id,
        claim_id,
        source_id,
        subject,
        source.reliability if source else Reliability.F,
        assertion.credibility if assertion else Credibility.CANNOT_BE_JUDGED,
        source,
        assertion,
        authenticity,
        tuple(dict.fromkeys(notes)),
    )


@dataclass(frozen=True, slots=True)
class FrozenSourceAssessment:
    assessment: ScopedSourceAssessment
    origin_group: OriginGroup
    relationships: tuple[AssessedOriginEdge, ...]
    origin_nodes: tuple[OriginNode, ...]
    observations: tuple[OriginObservation, ...]
    frozen_at: datetime
    origin_policy_version: str

    def to_dict(self) -> dict[str, Any]:
        """A detached JSON value; current corrections cannot change this snapshot."""
        result: dict[str, Any] = json.loads(json.dumps(asdict(self), default=_json_date))
        return result


def _json_date(value: object) -> str:
    if not isinstance(value, datetime):
        raise TypeError("Unsupported frozen assessment value.")
    return value.isoformat()


def freeze_source_assessment(
    assessment: ScopedSourceAssessment, origins: OriginAnalysis, *, frozen_at: datetime
) -> FrozenSourceAssessment:
    """Freeze new evidence only; callers must keep existing report snapshots unchanged."""
    assessment_time(frozen_at)
    matching = [
        node
        for node in origins.nodes
        if node.evidence_id == assessment.evidence_id and node.claim_id == assessment.claim_id
    ]
    if len(matching) != 1 or matching[0].source_id != assessment.source_id:
        raise ValueError("The frozen origin must match exactly one assessed evidence claim.")
    node = matching[0]
    group = next(group for group in origins.groups if node.id in group.member_ids)
    relationships = tuple(
        row
        for row in origins.relationships
        if row.edge.child_id in group.member_ids or row.edge.parent_id in group.member_ids
    )
    reviews: Sequence[SourceRatingRevision | AssertionRatingRevision | None] = (
        assessment.source_revision,
        assessment.assertion_revision,
    )
    if any(row is not None and row.review.recorded_at > frozen_at for row in reviews):
        raise ValueError("A snapshot cannot predate its applied rating revisions.")
    if any(row.edge.recorded_at > frozen_at for row in relationships):
        raise ValueError("A snapshot cannot predate its origin relationships.")
    observation_ids = {key for row in relationships for key in row.edge.observation_ids}
    endpoint_ids = set(group.member_ids) | {
        key for row in relationships for key in (row.edge.child_id, row.edge.parent_id)
    }
    return FrozenSourceAssessment(
        assessment,
        group,
        relationships,
        tuple(node for node in origins.nodes if node.id in endpoint_ids),
        tuple(row for row in origins.observations if row.id in observation_ids),
        frozen_at,
        origins.policy_version,
    )
