"""Reviewer corrections and source origins remain distinct qualitative inputs."""

from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest

from ase.application.reports.source_assessment_projection import (
    build_source_assessment_projection,
    prepare_source_assessment_targets,
)
from ase.application.reports.source_review_projection import freeze_reviewed_sources, review_target
from ase.domain.events import Credibility, Reliability
from ase.domain.origin_chains import analyse_origin_chains
from ase.domain.origin_records import OriginNode, OriginRole
from ase.domain.source_assessment import (
    ASSESSMENT_POLICY_VERSION,
    Assessor,
    RatingReview,
    RatingStatus,
)
from ase.domain.source_assessment_report import SourceAssessmentCapture
from ase.domain.source_review_records import (
    decode_review_snapshot,
    decode_source_review,
    encode_review_snapshot,
    encode_source_review,
)
from ase.domain.source_reviews import (
    SourceReviewKind,
    SourceReviewRevision,
    SourceReviewScope,
    source_review_key,
    validate_source_review_history,
)
from evidence_matrix_helpers import item, judgement
from report_documents_helpers import document_records
from source_assessment_helpers import NOW
from source_projection_helpers import BODY, EVIDENCE, SUBJECT


def decision(scope, target, *, number=1, previous=None, **changes):
    return SourceReviewRevision(
        scope,
        target,
        SourceReviewKind.RELIABILITY,
        number,
        RatingReview(
            str(uuid4()),
            Assessor.REVIEWER,
            str(scope.owner_id),
            RatingStatus.APPLIED,
            "Reviewed original methodology and correction record.",
            ASSESSMENT_POLICY_VERSION,
            NOW,
            NOW,
            previous,
        ),
        **{
            "reliability": Reliability.A,
            "expertise_basis": "Documented subject competence.",
            **changes,
        },
    )


def fixture():
    owner = uuid4()
    _, version = document_records(owner)
    version = replace(version, body=BODY, evidence=EVIDENCE)
    scope = SourceReviewScope(owner, None)
    return scope, version, review_target(version, "E1", BODY.key_judgements[0].id, SUBJECT)


@pytest.mark.parametrize("corruption", ["digest", "size", "payload"])
def test_bounded_history_codec_rejects_changed_bytes(corruption):
    scope, _, target = fixture()
    original = decision(scope, target)
    payload, digest, size = encode_source_review(original)
    assert decode_source_review(payload, digest, size) == original
    changed = {
        "digest": (payload, "0" * 64, size),
        "size": (payload, digest, size + 1),
        "payload": (payload.replace("methodology", "falsehood"), digest, size),
    }[corruption]
    with pytest.raises(ValueError):
        decode_source_review(*changed)


@pytest.mark.parametrize("corruption", ["scope", "subject", "date", "number", "policy"])
def test_history_rejects_broken_correction_chain(corruption):
    scope, _, target = fixture()
    first = decision(scope, target)
    second = decision(scope, target, number=2, previous=first.review.id)
    changed = {
        "scope": lambda: replace(second, scope=SourceReviewScope(uuid4(), None)),
        "subject": lambda: replace(second, target=replace(target, subject="another-subject")),
        "date": lambda: replace(
            second,
            review=replace(
                second.review,
                recorded_at=NOW - timedelta(days=1),
                reviewed_at=NOW - timedelta(days=1),
            ),
        ),
        "number": lambda: replace(second, number=3),
        "policy": lambda: replace(second, review=replace(second.review, policy_version="v2")),
    }[corruption]()
    with pytest.raises(ValueError, match="consecutive"):
        validate_source_review_history((first, changed))


def test_history_keys_separate_team_person_subject_and_claim_axes():
    scope, _, target = fixture()
    other = SourceReviewScope(uuid4(), None)
    team = SourceReviewScope(scope.owner_id, uuid4())
    for kind in SourceReviewKind:
        assert len({source_review_key(s, kind, target) for s in (scope, other, team)}) == 3
        assert source_review_key(team, kind, target) == source_review_key(
            replace(team, owner_id=other.owner_id), kind, target
        )
    changed = replace(target, report_version_id=uuid4(), capture_id="new", claim_id="new")
    assert source_review_key(scope, SourceReviewKind.RELIABILITY, target) == source_review_key(
        scope, SourceReviewKind.RELIABILITY, changed
    )
    for kind in (SourceReviewKind.CREDIBILITY, SourceReviewKind.AUTHENTICITY):
        assert source_review_key(scope, kind, target) != source_review_key(scope, kind, changed)


class Histories:
    def __init__(self, values):
        self.values = {row.key: (row,) for row in values}

    async def history(self, scope, key):
        return self.values.get(key, ())


async def test_one_strong_original_and_three_weak_copies_keep_one_origin_and_their_own_grades():
    scope, version, _ = fixture()
    evidence = tuple(replace(item(f"E{i}", "A1"), source_id=f"publisher-{i}") for i in range(1, 5))
    body = replace(BODY, key_judgements=(judgement("E1", "E2", "E3", "E4"),))
    version = replace(version, evidence=evidence, body=body)
    subjects = {body.key_judgements[0].id: SUBJECT}
    targets = prepare_source_assessment_targets(version.id, body, evidence, subjects=subjects)
    claim = targets.claims[0]
    nodes = tuple(
        OriginNode(
            row.label,
            row.capture_id,
            claim.claim_id,
            row.source_id,
            OriginRole.ORIGINAL_DOCUMENT if row.label == "E1" else OriginRole.DERIVED,
            row.declared_organisation,
            "retained-original-document",
        )
        for row in targets.evidence
    )
    baseline = build_source_assessment_projection(
        targets, frozen_at=NOW, origins=analyse_origin_chains(nodes, [])
    )
    version.source_assessment = SourceAssessmentCapture(version.id, NOW, "captured", baseline)
    revisions = []
    for row in targets.evidence:
        target = review_target(version, row.label, claim.judgement_id, SUBJECT)
        revisions.append(
            decision(
                scope, target, reliability=Reliability.A if row.label == "E1" else Reliability.D
            )
        )
        revisions.append(
            replace(
                decision(scope, target),
                kind=SourceReviewKind.CREDIBILITY,
                reliability=None,
                expertise_basis=None,
                credibility=Credibility.CONFIRMED if row.label == "E1" else Credibility.DOUBTFUL,
            )
        )
    snapshot = await freeze_reviewed_sources(
        Histories(revisions), version, scope, scope.owner_id, subjects, NOW
    )
    grades = {
        (row.reliability.value, int(row.credibility)) for row in snapshot.projection.assessments
    }
    assert grades == {("A", 1), ("D", 4)}
    assert sum(row.reliability is Reliability.A for row in snapshot.projection.assessments) == 1
    assert len(snapshot.projection.origins.groups) == 1
    assert len(snapshot.projection.origins.groups[0].member_ids) == 4
    assert version.body == body and version.evidence == evidence
    assert snapshot.projection.origins == baseline.origins
    assert decode_review_snapshot(*encode_review_snapshot(snapshot)) == snapshot
    assert all(row.reliability is Reliability.F for row in baseline.assessments)
