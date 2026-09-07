"""Report-scoped operator identity decisions, without automatic entity merging."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from ase.domain.claim_revisions import (
    ClaimCitation,
    ClaimCitationInput,
    _validate_frozen_citations,
    freeze_claim_citations,
)
from ase.domain.evidence_attributes import EvidenceAttribute, evidence_attributes_to_list
from ase.domain.report_records import ReportVersion
from ase.domain.research_context import (
    ALIAS_KEYS,
    IDENTIFIER_KEYS,
    RESEARCH_CONTEXT_VERSION,
    CapturedIdentityValue,
    ResearchIdentityCandidate,
)


class IdentityDisposition(StrEnum):
    MATCHED = "matched"
    REJECTED = "rejected"
    UNRESOLVED = "unresolved"
    WITHDRAWN = "withdrawn"


@dataclass(frozen=True, slots=True)
class IdentityCandidateSnapshot:
    candidate: ResearchIdentityCandidate
    event_id: str
    source_id: str
    source_content_hash: str
    # Preserve the original fields, including registry/jurisdiction assertions
    # omitted from historical context projections. Missing fields remain absent.
    attributes: tuple[EvidenceAttribute, ...]


def freeze_identity_candidate(version: ReportVersion, label: str) -> IdentityCandidateSnapshot:
    context = version.research_context
    if context is None or context.method_version != RESEARCH_CONTEXT_VERSION:
        raise ValueError("This version has no captured identity candidates")
    candidates = [item for item in context.identity_candidates if item.evidence_label == label]
    evidence = [item for item in version.evidence if item.label == label]
    if len(candidates) != 1 or len(evidence) != 1:
        raise ValueError("Choose one unambiguous captured identity candidate")
    candidate, item = candidates[0], evidence[0]
    snapshot = IdentityCandidateSnapshot(
        candidate, item.event_id, item.source_id, item.content_hash, item.attributes
    )
    validate_identity_candidate(snapshot)
    return snapshot


@dataclass(frozen=True, slots=True)
class IdentityDecisionRevision:
    id: UUID
    decision_id: UUID
    report_id: UUID
    report_version_id: UUID
    number: int
    previous_id: UUID | None
    subject: str
    candidate: IdentityCandidateSnapshot
    disposition: IdentityDisposition
    rationale: str
    unresolved_conflicts: tuple[str, ...]
    citations: tuple[ClaimCitation, ...]
    authored_by: UUID
    created_at: datetime


def _text(value: str, limit: int) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError("Identity review text is empty or oversized")
    value.encode("utf-8")
    if any(ord(char) < 32 and char not in "\n\r\t" for char in value):
        raise ValueError("Identity review text contains invalid control characters")


def validate_identity_candidate(value: IdentityCandidateSnapshot) -> None:
    if not isinstance(value, IdentityCandidateSnapshot):
        raise ValueError("Invalid identity candidate snapshot")
    for field in (value.event_id, value.source_id, value.source_content_hash):
        _text(field, 500)
    if not isinstance(value.attributes, tuple) or any(
        not isinstance(item, EvidenceAttribute) for item in value.attributes
    ):
        raise ValueError("Candidate attributes must be immutable")
    evidence_attributes_to_list(value.attributes)
    attributes = {item.key: item.value for item in value.attributes}
    candidate = value.candidate
    if (
        not isinstance(candidate, ResearchIdentityCandidate)
        or candidate.status != "unverified_candidate"
    ):
        raise ValueError("Invalid captured candidate status")
    _text(candidate.evidence_label, 64)
    for values, allowed in (
        (candidate.identifiers, IDENTIFIER_KEYS),
        (candidate.aliases, ALIAS_KEYS),
    ):
        if not isinstance(values, tuple) or len(values) > len(allowed):
            raise ValueError("Candidate identities must be bounded immutable collections")
        seen = set()
        for item in values:
            if not isinstance(item, CapturedIdentityValue) or item.namespace not in allowed:
                raise ValueError("Invalid candidate identifier namespace")
            _text(item.value, 4000)
            if item.namespace in seen or attributes.get(item.namespace) != item.value:
                raise ValueError("Candidate identifier differs from frozen evidence")
            seen.add(item.namespace)
    if not candidate.identifiers and not candidate.aliases:
        raise ValueError("Candidate has no captured identity")
    if candidate.declared_match_status is not None:
        _text(candidate.declared_match_status, 4000)
        if attributes.get("identity_match") != candidate.declared_match_status:
            raise ValueError("Candidate match status differs from frozen evidence")


def validate_identity_revision(value: IdentityDecisionRevision) -> None:
    if not isinstance(value, IdentityDecisionRevision):
        raise ValueError("Invalid identity decision revision")
    for identity in (
        value.id,
        value.decision_id,
        value.report_id,
        value.report_version_id,
        value.authored_by,
    ):
        if not isinstance(identity, UUID):
            raise ValueError("Invalid identity decision identifier")
    if type(value.number) is not int or not 1 <= value.number <= 100:
        raise ValueError("Invalid identity revision number")
    if not isinstance(value.disposition, IdentityDisposition):
        raise ValueError("Invalid identity disposition")
    if value.number == 1:
        if value.previous_id is not None or value.disposition is IdentityDisposition.WITHDRAWN:
            raise ValueError("Invalid initial identity decision")
    elif not isinstance(value.previous_id, UUID) or value.previous_id == value.id:
        raise ValueError("Invalid identity revision predecessor")
    if not isinstance(value.created_at, datetime) or value.created_at.utcoffset() is None:
        raise ValueError("Invalid identity audit timestamp")
    _text(value.subject, 4000)
    _text(value.rationale, 1200)
    if not isinstance(value.unresolved_conflicts, tuple) or len(value.unresolved_conflicts) > 20:
        raise ValueError("Invalid identity conflict collection")
    for conflict in value.unresolved_conflicts:
        _text(conflict, 1200)
    validate_identity_candidate(value.candidate)
    _identity_citations(value.citations)


def _identity_citations(citations: tuple[ClaimCitation, ...]) -> None:
    if not isinstance(citations, tuple):
        raise ValueError("Identity citations must be immutable")
    if citations:
        _validate_frozen_citations(citations)


def revise_identity_decision(
    *,
    version: ReportVersion,
    revision_id: UUID,
    decision_id: UUID,
    previous: IdentityDecisionRevision | None,
    subject: str,
    candidate_label: str,
    disposition: IdentityDisposition,
    rationale: str,
    unresolved_conflicts: tuple[str, ...],
    citations: tuple[ClaimCitationInput, ...],
    actor_id: UUID,
    now: datetime,
) -> IdentityDecisionRevision:
    """The service supplies the frozen subject, IDs and time after fresh scope checks.

    A matched disposition is an attributed judgement about this report's subject.
    It establishes neither ownership nor transitive identity with other records.
    """
    for identity in (revision_id, decision_id, actor_id, version.id, version.report_id):
        if not isinstance(identity, UUID):
            raise ValueError("Identity review requires server-issued identifiers")
    if not isinstance(disposition, IdentityDisposition):
        raise ValueError("Invalid identity review disposition")
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise ValueError("Identity review time must include a timezone")
    _text(subject, 4000)
    _text(rationale, 1200)
    if not isinstance(unresolved_conflicts, tuple) or len(unresolved_conflicts) > 20:
        raise ValueError("Identity review conflicts must be bounded")
    for conflict in unresolved_conflicts:
        _text(conflict, 1200)
    if not isinstance(citations, tuple) or len(citations) > 20:
        raise ValueError("Identity review citations must be bounded")
    candidate = freeze_identity_candidate(version, candidate_label)
    frozen = freeze_claim_citations(version, citations) if citations else ()
    if previous is None:
        if disposition is IdentityDisposition.WITHDRAWN:
            raise ValueError("An initial identity decision cannot be withdrawn")
        number = 1
    else:
        validate_identity_revision(previous)
        if (
            previous.decision_id != decision_id
            or previous.report_id != version.report_id
            or previous.report_version_id != version.id
            or previous.subject != subject
            or previous.candidate != candidate
            or previous.id == revision_id
            or previous.created_at > now
        ):
            raise ValueError("Identity corrections must preserve their original anchors")
        number = previous.number + 1
        if number > 100:
            raise ValueError("Identity decision history is full")
    result = IdentityDecisionRevision(
        revision_id,
        decision_id,
        version.report_id,
        version.id,
        number,
        previous.id if previous else None,
        subject,
        candidate,
        disposition,
        rationale,
        unresolved_conflicts,
        frozen,
        actor_id,
        now,
    )
    validate_identity_revision(result)
    return result
