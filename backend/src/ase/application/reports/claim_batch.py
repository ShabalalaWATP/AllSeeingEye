"""Frozen admission anchor and all-or-nothing construction of model proposals."""

import json
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from uuid import UUID, uuid4

from ase.application.reports.claim_proposals import MAX_PROPOSALS, ClaimProposal
from ase.domain.claim_origin import ClaimModelOrigin
from ase.domain.claim_revisions import ClaimReviewState, ClaimRevision, revise_claim
from ase.domain.report_records import ReportVersion, body_to_dict


@dataclass(frozen=True, slots=True)
class ClaimBatchAnchor:
    actor_id: UUID
    owner_id: UUID
    team_id: UUID | None
    report_id: UUID
    version_id: UUID
    version_number: int
    body_sha256: str
    version: ReportVersion
    evidence_sha256: str


def claim_body_digest(version: ReportVersion) -> str:
    payload = json.dumps(
        body_to_dict(version.body),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return sha256(payload.encode("utf-8")).hexdigest()


def build_proposal_batch(
    version: ReportVersion,
    proposals: tuple[ClaimProposal, ...],
    origin: ClaimModelOrigin,
    actor_id: UUID,
    now: datetime,
) -> tuple[ClaimRevision, ...]:
    """Validate every revision before persistence can write any of the batch."""
    if not 1 <= len(proposals) <= MAX_PROPOSALS:
        raise ValueError("A proposal batch must contain one to twenty claims")
    if len({item.statement for item in proposals}) != len(proposals):
        raise ValueError("Duplicate statements in proposal batch")
    return tuple(
        revise_claim(
            version=version,
            revision_id=uuid4(),
            claim_id=uuid4(),
            previous=None,
            statement=item.statement,
            kind=item.kind,
            state=ClaimReviewState.PROPOSED,
            citations=item.citations,
            unresolved_conflicts=item.unresolved_conflicts,
            reason="Model proposal awaiting operator review.",
            actor_id=actor_id,
            now=now,
            model_origin=origin,
        )
        for item in proposals
    )
