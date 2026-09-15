"""A01 scoped grades, issuer authenticity, review precedence and conservative contribution."""

from dataclasses import replace
from datetime import timedelta

import pytest

from ase.domain.doctrine import Confidence
from ase.domain.events import Credibility, Reliability
from ase.domain.evidence_matrix import Contribution, contribution_for
from ase.domain.judgement_assessment import assess_judgement
from ase.domain.source_assessment import (
    Assessor,
    Authenticity,
    IssuerAuthenticity,
    RatingStatus,
)
from ase.domain.source_assessment_policy import append_rating_revision, resolve_source_assessment
from evidence_matrix_helpers import item, judgement
from source_assessment_helpers import NOW, assertion, review, source


def resolve(**changes):
    return resolve_source_assessment(
        **{
            "evidence_id": "E1",
            "claim_id": "C1",
            "source_id": "statistics-office",
            "subject": "population-statistics",
            **changes,
        }
    )


@pytest.mark.parametrize("country", ["GB", "US", "RU", "CN", "UA"])
def test_authentic_government_release_never_confers_assertion_truth(country):
    source_id = f"government-{country}"
    authenticity = IssuerAuthenticity(
        "E1",
        source_id,
        Authenticity.ESTABLISHED,
        "Captured official publication receipt.",
        "capture-1",
    )
    result = resolve(source_id=source_id, authenticity=authenticity)
    assert result.reliability is Reliability.F
    assert result.credibility is Credibility.CANNOT_BE_JUDGED
    assert result.authenticity is authenticity
    assert contribution_for(result.reliability, result.credibility) is Contribution.UNASSESSED


def test_source_expertise_applies_to_dataset_but_not_an_unrelated_opinion():
    history = (source(),)
    dataset = resolve(source_history=history, assertion_history=(assertion(),))
    opinion = resolve(subject="foreign-policy-opinion", source_history=history)
    assert dataset.reliability is Reliability.A and dataset.credibility is Credibility.CONFIRMED
    assert contribution_for(dataset.reliability, dataset.credibility) is Contribution.STRONG
    assert opinion.reliability is Reliability.F
    assert opinion.credibility is Credibility.CANNOT_BE_JUDGED
    assert history[0].reliability is Reliability.A


def test_assertion_grade_never_transfers_to_another_capture_or_claim():
    for changed in ({"claim_id": "C2"}, {"evidence_id": "E2"}):
        result = resolve(assertion_history=(assertion(),), **changed)
        assert result.credibility is Credibility.CANNOT_BE_JUDGED


def test_one_strong_source_beats_three_weak_tabloids_using_unchanged_matrix():
    strong = resolve(source_history=(source(),), assertion_history=(assertion(),))
    weak = resolve(
        source_history=(source(Reliability.E),),
        assertion_history=(assertion(Credibility.POSSIBLY_TRUE),),
    )
    strong_item = replace(
        item("E1"), reliability=strong.reliability, credibility=strong.credibility
    )
    weak_items = [
        replace(item(f"E{i}"), reliability=weak.reliability, credibility=weak.credibility)
        for i in range(2, 5)
    ]
    assert (
        assess_judgement(judgement("E1"), [strong_item]).confidence_ceiling is Confidence.MODERATE
    )
    assert (
        assess_judgement(judgement("E2", "E3", "E4"), weak_items).confidence_ceiling
        is Confidence.LOW
    )
    result = assess_judgement(judgement("E1", "E2", "E3", "E4"), [strong_item, *weak_items])
    assert result.confidence_ceiling is Confidence.MODERATE


def test_contradictory_official_releases_remain_opposition_not_corroboration():
    support = item("E1", "A2", "official-one")
    opposition = item("E2", "A2", "official-two")
    result = assess_judgement(judgement("E1", opposition=("E2",)), [support, opposition])
    assert result.confidence_ceiling is Confidence.LOW
    assert result.status == "contested" and result.contradicting_labels == ("E2",)


@pytest.mark.parametrize("assessor", [Assessor.MODEL, Assessor.THIRD_PARTY])
def test_external_grade_is_a_proposal_and_cannot_apply_itself(assessor):
    with pytest.raises(ValueError, match="proposals"):
        review(assessor=assessor)
    candidate = source(review=review(assessor=assessor, status=RatingStatus.PROPOSAL))
    assert resolve(source_history=(candidate,)).reliability is Reliability.F


def test_reviewed_grade_survives_model_and_policy_updates_until_explicit_human_revision():
    first = source(review=review(assessor=Assessor.REVIEWER, reviewed_at=NOW))
    proposal = source(
        Reliability.E,
        review=review(
            "r2",
            assessor=Assessor.MODEL,
            status=RatingStatus.PROPOSAL,
            supersedes="r1",
        ),
    )
    history = append_rating_revision((first,), proposal)
    assert resolve(source_history=history).reliability is Reliability.A
    assert "proposals" in " ".join(resolve(source_history=history).review_notes)
    with pytest.raises(ValueError, match="overwrite"):
        append_rating_revision(history, source(Reliability.E, review=review("r3", supersedes="r2")))
    accepted = source(
        Reliability.C,
        review=review(
            "r3",
            assessor=Assessor.REVIEWER,
            reviewed_at=NOW,
            supersedes="r2",
            basis="Reviewed new correction history and narrowed source competence.",
        ),
    )
    updated = append_rating_revision(history, accepted)
    assert resolve(source_history=updated).reliability is Reliability.C
    assert "Unapplied" not in " ".join(resolve(source_history=updated).review_notes)
    assert history == (first, proposal)


def test_assertion_reviews_have_the_same_precedence_rule():
    first = assertion(review=review("a1", assessor=Assessor.REVIEWER, reviewed_at=NOW))
    candidate = assertion(Credibility.DOUBTFUL, review=review("a2", supersedes="a1"))
    with pytest.raises(ValueError, match="overwrite"):
        append_rating_revision((first,), candidate)


def test_policy_transition_requires_a_note_and_preserves_old_revision():
    inherited = source(review=review(policy_version="inherited-feed-v1"))
    assert resolve(source_history=(inherited,)).reliability is Reliability.A
    assert "inherited" in " ".join(resolve(source_history=(inherited,)).review_notes)
    changed = source(Reliability.B, review=review("r2", supersedes="r1"))
    with pytest.raises(ValueError, match="policy change"):
        append_rating_revision((inherited,), changed)
    changed = replace(
        changed, review=replace(changed.review, policy_note="New scoped policy review.")
    )
    history = append_rating_revision((inherited,), changed)
    assert history[0] is inherited and history[0].review.policy_version == "inherited-feed-v1"


def test_legacy_unknown_competence_needs_explicit_note_and_never_invents_expertise():
    inherited = source(
        Reliability.C,
        expertise_basis=None,
        review=review(
            assessor=Assessor.LEGACY,
            policy_version="legacy-feed-v1",
            policy_note="Retained inherited C4 policy; no current source review exists.",
        ),
    )
    result = resolve(source_history=(inherited,))
    assert result.reliability is Reliability.C and result.source_revision.expertise_basis is None
    assert "undocumented" in " ".join(result.review_notes)
    with pytest.raises(ValueError, match="Unknown subject competence"):
        source(expertise_basis=None)
    assert source(Reliability.F, expertise_basis=None).reliability is Reliability.F


@pytest.mark.parametrize(
    "changes",
    [
        {"id": ""},
        {"basis": "  "},
        {"policy_version": ""},
        {"assessor": "policy"},
        {"status": "applied"},
        {"recorded_at": NOW.replace(tzinfo=None)},
        {"reviewed_at": NOW},
        {"assessor": Assessor.REVIEWER},
        {"assessor": Assessor.REVIEWER, "reviewed_at": NOW + timedelta(seconds=1)},
        {"supersedes": "r1"},
    ],
)
def test_invalid_review_metadata_is_rejected(changes):
    with pytest.raises(ValueError):
        review(**changes)


@pytest.mark.parametrize(
    "changes",
    [
        {"source_id": "other"},
        {"subject": "other"},
        {"review": review("r2", supersedes="missing")},
        {"review": review("r2", recorded_at=NOW - timedelta(seconds=1), supersedes="r1")},
        {"review": review()},
    ],
)
def test_revision_history_rejects_scope_rewrites_forks_duplicates_and_time_reversal(changes):
    with pytest.raises(ValueError):
        append_rating_revision((source(),), source(**changes))


@pytest.mark.parametrize("kind", ["authenticity", "source", "assertion"])
def test_typed_grades_and_publication_identity_cannot_be_forged(kind):
    with pytest.raises(ValueError):
        if kind == "authenticity":
            resolve(
                authenticity=IssuerAuthenticity(
                    "other", "other", Authenticity.UNASSESSED, "Unknown."
                )
            )
        elif kind == "source":
            source(grade="A")
        else:
            assertion(grade=True)
