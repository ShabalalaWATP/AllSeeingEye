"""Immutable claim annotations anchored to one frozen report version.

Atomicity and semantic support require review. Literal locators establish only
which captured text was cited, never that the assertion is true.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from hashlib import sha256
from typing import Literal
from uuid import UUID

from ase.domain.citation_checks import FrozenExcerpt
from ase.domain.claim_origin import ClaimModelOrigin
from ase.domain.report_records import ReportVersion


class ClaimKind(StrEnum):
    REPORTED_FACT = "reported_fact"
    ANALYTICAL_INFERENCE = "analytical_inference"


class ClaimReviewState(StrEnum):
    PROPOSED = "proposed"
    REVIEWED = "reviewed"
    WITHDRAWN = "withdrawn"


class ClaimRelation(StrEnum):
    SUPPORTING = "supporting"
    OPPOSING = "opposing"
    CONTEXT = "context"


@dataclass(frozen=True, slots=True)
class ClaimCitationInput:
    label: str
    relation: ClaimRelation
    field: str
    start: int
    end: int
    text: str


@dataclass(frozen=True, slots=True)
class ClaimCitation:
    label: str
    relation: ClaimRelation
    event_id: str
    source_content_hash: str
    excerpt: FrozenExcerpt


@dataclass(frozen=True, slots=True)
class ClaimRevision:
    id: UUID
    claim_id: UUID
    report_id: UUID
    report_version_id: UUID
    number: int
    previous_id: UUID | None
    statement: str
    kind: ClaimKind
    state: ClaimReviewState
    citations: tuple[ClaimCitation, ...]
    unresolved_conflicts: tuple[str, ...]
    reason: str
    authored_by: UUID
    created_at: datetime
    model_origin: ClaimModelOrigin | None = None


def _text(value: str, limit: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError("Claim text is empty or exceeds its bound")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("Claim text must be valid Unicode") from exc
    if any(ord(char) < 32 and char not in "\n\r\t" for char in value):
        raise ValueError("Claim text contains unsupported control characters")
    return value


def freeze_claim_citations(
    version: ReportVersion, citations: tuple[ClaimCitationInput, ...]
) -> tuple[ClaimCitation, ...]:
    if not 1 <= len(citations) <= 20:
        raise ValueError("A claim requires between one and twenty citations")
    evidence = {item.label: item for item in version.evidence}
    if len(evidence) != len(version.evidence):
        raise ValueError("Ambiguous frozen evidence labels")
    frozen = []
    seen = set()
    for citation in citations:
        item = evidence.get(citation.label)
        if item is None or citation.field not in ("title", "summary"):
            raise ValueError("Citation must identify original frozen evidence text")
        if not isinstance(citation.relation, ClaimRelation):
            raise ValueError("Invalid citation relation")
        source_field: Literal["title", "summary"] = (
            "title" if citation.field == "title" else "summary"
        )
        source = item.title if source_field == "title" else item.summary
        start, end = citation.start, citation.end
        if (
            type(start) is not int
            or type(end) is not int
            or source is None
            or not 0 <= start < end <= len(source)
            or end - start > 1200
            or source[start:end] != citation.text
            or not citation.text.strip()
        ):
            raise ValueError("Excerpt does not match its exact frozen text locator")
        identity = (citation.label, citation.relation, citation.field, start, end)
        if identity in seen:
            raise ValueError("Duplicate claim citation")
        seen.add(identity)
        frozen.append(
            ClaimCitation(
                citation.label,
                citation.relation,
                item.event_id,
                item.content_hash,
                FrozenExcerpt(
                    source_field,
                    start,
                    end,
                    citation.text,
                    sha256(citation.text.encode("utf-8")).hexdigest(),
                ),
            )
        )
    return tuple(frozen)


def revise_claim(
    *,
    version: ReportVersion,
    revision_id: UUID,
    claim_id: UUID,
    previous: ClaimRevision | None,
    statement: str,
    kind: ClaimKind,
    state: ClaimReviewState,
    citations: tuple[ClaimCitationInput, ...],
    unresolved_conflicts: tuple[str, ...],
    reason: str,
    actor_id: UUID,
    now: datetime,
    model_origin: ClaimModelOrigin | None = None,
) -> ClaimRevision:
    """Caller supplies fresh access checks and serialises optimistic revision writes."""
    if now.utcoffset() is None:
        raise ValueError("Claim audit time must be timezone-aware")
    if not isinstance(kind, ClaimKind) or not isinstance(state, ClaimReviewState):
        raise ValueError("Invalid claim kind or review state")
    unresolved_conflicts = tuple(unresolved_conflicts)
    if len(unresolved_conflicts) > 20:
        raise ValueError("Too many unresolved conflicts")
    for conflict in unresolved_conflicts:
        _text(conflict, 1200)
    if previous is not None:
        if model_origin is not None and model_origin != previous.model_origin:
            raise ValueError("A correction cannot replace its original model provenance")
        model_origin = previous.model_origin
        if (
            previous.claim_id != claim_id
            or previous.report_id != version.report_id
            or previous.report_version_id != version.id
            or previous.id == revision_id
            or now < previous.created_at
        ):
            raise ValueError("Correction must retain its claim, frozen version and audit order")
    elif state is not ClaimReviewState.PROPOSED:
        raise ValueError("New assertions require a separate review revision")
    if model_origin is not None:
        model_origin.validate()
        if model_origin.generated_at > now:
            raise ValueError("Model provenance cannot postdate its claim")
    return ClaimRevision(
        revision_id,
        claim_id,
        version.report_id,
        version.id,
        previous.number + 1 if previous else 1,
        previous.id if previous else None,
        _text(statement, 1200),
        kind,
        state,
        freeze_claim_citations(version, citations),
        unresolved_conflicts,
        _text(reason, 1200),
        actor_id,
        now,
        model_origin,
    )


def validate_claim_revision(value: ClaimRevision) -> None:
    """Validate stored structure; the application must also recheck frozen evidence."""
    for identity in (
        value.id,
        value.claim_id,
        value.report_id,
        value.report_version_id,
        value.authored_by,
    ):
        if not isinstance(identity, UUID):
            raise ValueError("Invalid claim identity")
    if (
        type(value.number) is not int
        or value.number < 1
        or not isinstance(value.created_at, datetime)
        or value.created_at.utcoffset() is None
    ):
        raise ValueError("Invalid claim revision number or audit time")
    if value.number == 1:
        if value.previous_id is not None or value.state is not ClaimReviewState.PROPOSED:
            raise ValueError("Invalid initial claim state")
    elif not isinstance(value.previous_id, UUID) or value.previous_id == value.id:
        raise ValueError("Invalid preceding revision")
    if not isinstance(value.kind, ClaimKind) or not isinstance(value.state, ClaimReviewState):
        raise ValueError("Invalid claim kind or state")
    if value.model_origin is not None:
        if not isinstance(value.model_origin, ClaimModelOrigin):
            raise ValueError("Invalid model origin")
        value.model_origin.validate()
        if value.model_origin.generated_at > value.created_at:
            raise ValueError("Model provenance cannot postdate its claim")
    _text(value.statement, 1200)
    _text(value.reason, 1200)
    if not isinstance(value.unresolved_conflicts, tuple) or len(value.unresolved_conflicts) > 20:
        raise ValueError("Invalid frozen conflicts")
    for conflict in value.unresolved_conflicts:
        _text(conflict, 1200)
    _validate_frozen_citations(value.citations)


def _validate_frozen_citations(citations: tuple[ClaimCitation, ...]) -> None:
    if not isinstance(citations, tuple) or not 1 <= len(citations) <= 20:
        raise ValueError("Invalid frozen citations")
    seen = set()
    for citation in citations:
        if not isinstance(citation, ClaimCitation) or not isinstance(
            citation.relation, ClaimRelation
        ):
            raise ValueError("Invalid frozen citation")
        _text(citation.label, 32)
        _text(citation.event_id, 500)
        _text(citation.source_content_hash, 128)
        excerpt = citation.excerpt
        if (
            not isinstance(excerpt, FrozenExcerpt)
            or excerpt.field not in ("title", "summary")
            or type(excerpt.start) is not int
            or type(excerpt.end) is not int
            or not 0 <= excerpt.start < excerpt.end
            or excerpt.end - excerpt.start != len(excerpt.text)
        ):
            raise ValueError("Invalid frozen excerpt locator")
        _text(excerpt.text, 1200)
        if sha256(excerpt.text.encode("utf-8")).hexdigest() != excerpt.sha256:
            raise ValueError("Invalid frozen excerpt hash")
        identity = (citation.label, citation.relation, excerpt.field, excerpt.start, excerpt.end)
        if identity in seen:
            raise ValueError("Duplicate frozen citation")
        seen.add(identity)
