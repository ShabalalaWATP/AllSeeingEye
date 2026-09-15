"""Report integration preserves capture/claim scope without mutating shared evidence."""

from dataclasses import replace
from datetime import timedelta
from itertools import permutations
from uuid import UUID

import pytest

from ase.application.reports.source_assessment_projection import (
    build_source_assessment_projection,
    prepare_source_assessment_targets,
    restore_source_assessment_projection,
)
from ase.domain.doctrine import Confidence
from ase.domain.events import Credibility, Reliability
from ase.domain.origin_chains import analyse_origin_chains
from ase.domain.origin_records import OriginRole
from ase.domain.reports import ReportBody
from ase.domain.source_assessment import Assessor, RatingStatus
from ase.domain.source_assessment_records import (
    SourceAssessmentSnapshotError,
    source_assessment_report_to_dict,
)
from evidence_matrix_helpers import judgement
from source_assessment_helpers import NOW, assertion, node, review, source
from source_projection_helpers import BODY, EVIDENCE, SUBJECT, VERSION, projection, targets


def test_preparation_exposes_stable_version_and_content_bound_review_keys():
    first = targets()
    assert first == targets()
    assert first.evidence[0].capture_id != EVIDENCE[0].event_id
    assert first.claims[0].claim_id != BODY.key_judgements[0].id
    assert first.claims[0].uses[0].capture_id == first.evidence[0].capture_id
    other = targets(version=UUID("00000000-0000-4000-8000-000000000002"))
    assert first.evidence[0].capture_id != other.evidence[0].capture_id
    assert first.claims[0].claim_id != other.claims[0].claim_id


def test_amended_capture_with_unchanged_event_id_and_content_hash_gets_a_new_review_key():
    amended = replace(EVIDENCE[0], summary="A corrected captured statement.")
    assert (
        amended.event_id == EVIDENCE[0].event_id
        and amended.content_hash == EVIDENCE[0].content_hash
    )
    assert targets(evidence=(amended,)).evidence[0].capture_id != targets().evidence[0].capture_id


def test_one_article_receives_different_grades_for_two_claims_without_changing_the_article():
    body = ReportBody(
        key_judgements=(
            judgement("E1"),
            replace(judgement("E1"), id="KJ2", statement="A different claim."),
        )
    )
    prepared = targets(body=body, subjects={"KJ1": SUBJECT, "KJ2": "foreign-policy"})
    capture = prepared.evidence[0].capture_id
    first, second = prepared.claims
    histories = {
        (capture, first.claim_id): (assertion(evidence_id=capture, claim_id=first.claim_id),),
        (capture, second.claim_id): (
            assertion(Credibility.DOUBTFUL, evidence_id=capture, claim_id=second.claim_id),
        ),
    }
    result = build_source_assessment_projection(
        prepared,
        frozen_at=NOW,
        source_histories={("statistics-office", SUBJECT): (source(),)},
        assertion_histories=histories,
    )
    assert [(row.reliability, row.credibility) for row in result.assessments] == [
        (Reliability.A, Credibility.CONFIRMED),
        (Reliability.F, Credibility.DOUBTFUL),
    ]
    assert EVIDENCE[0].reliability == "A" and EVIDENCE[0].credibility == 1


def test_missing_scoped_reviews_do_not_implicitly_adopt_inherited_event_grades():
    result = projection(rated=False)
    assert result.assessments[0].reliability is Reliability.F
    assert result.assessments[0].credibility is Credibility.CANNOT_BE_JUDGED
    assert result.origins.nodes[0].role is OriginRole.UNKNOWN
    assert result.origins.groups[0].review_required
    assert EVIDENCE[0].reliability == "A" and EVIDENCE[0].credibility == 1


def test_explicit_legacy_adapter_revisions_preserve_grades_and_disclose_the_policy():
    prepared = targets()
    capture, claim = prepared.evidence[0].capture_id, prepared.claims[0].claim_id
    note = "Imported retained feed policy; competence has not been reviewed."
    source_revision = source(
        Reliability.C,
        expertise_basis=None,
        review=review(
            assessor=Assessor.LEGACY,
            policy_version="legacy-feed-v1",
            policy_note=note,
        ),
    )
    assertion_revision = assertion(
        Credibility.DOUBTFUL,
        evidence_id=capture,
        claim_id=claim,
        review=review("a1", assessor=Assessor.LEGACY, policy_version="legacy-item-v1"),
    )
    result = build_source_assessment_projection(
        prepared,
        frozen_at=NOW,
        source_histories={("statistics-office", SUBJECT): (source_revision,)},
        assertion_histories={(capture, claim): (assertion_revision,)},
    )
    row = result.assessments[0]
    assert row.reliability is Reliability.C and row.credibility is Credibility.DOUBTFUL
    assert note in row.review_notes and row.source_revision.review.reviewed_at is None


def test_both_support_and_opposition_are_frozen_for_the_same_capture_without_duplicate_grades():
    body = ReportBody(key_judgements=(judgement("E1", opposition=("E1",)),))
    prepared = targets(body=body)
    assert prepared.claims[0].uses[0].roles == ("contradicting", "supporting")
    assert len(build_source_assessment_projection(prepared, frozen_at=NOW).assessments) == 1


def test_permuted_evidence_input_has_identical_preparation_and_projection():
    evidence = (
        *EVIDENCE,
        replace(EVIDENCE[0], label="E2", event_id="event-2", title="Another observation."),
    )
    body = ReportBody(key_judgements=(judgement("E1", "E2"),))
    expected = targets(body=body, evidence=evidence)
    for ordered in permutations(evidence):
        assert targets(body=body, evidence=ordered) == expected


@pytest.mark.parametrize(
    "changes",
    [
        {"subjects": {}},
        {"subjects": {"KJ1": " "}},
        {"subjects": {"KJ1": SUBJECT, "unknown": SUBJECT}},
        {"body": ReportBody(key_judgements=(judgement("missing"),))},
        {"body": ReportBody(key_judgements=(judgement("E1"), judgement("E1")))},
        {"evidence": (EVIDENCE[0], EVIDENCE[0])},
    ],
)
def test_preparation_rejects_missing_scope_fabricated_citations_and_duplicate_records(changes):
    with pytest.raises(ValueError):
        prepare_source_assessment_targets(
            **{
                "report_version_id": VERSION,
                "body": BODY,
                "evidence": EVIDENCE,
                "subjects": {"KJ1": SUBJECT},
                **changes,
            }
        )


@pytest.mark.parametrize(
    "kind", ["wrong_source_key", "wrong_source_scope", "old_assertion_capture", "future_proposal"]
)
def test_review_store_cannot_supply_unrequested_stale_or_future_scopes(kind):
    prepared = targets()
    source_histories, assertion_histories = {}, {}
    scope = prepared.evidence[0].capture_id, prepared.claims[0].claim_id
    if kind == "wrong_source_key":
        source_histories[("other", SUBJECT)] = (source(),)
    elif kind == "wrong_source_scope":
        source_histories[("statistics-office", SUBJECT)] = (source(subject="other"),)
    elif kind == "old_assertion_capture":
        assertion_histories[scope] = (assertion(),)
    else:
        source_histories[("statistics-office", SUBJECT)] = (
            source(
                review=review(
                    assessor=Assessor.MODEL,
                    status=RatingStatus.PROPOSAL,
                    recorded_at=NOW + timedelta(seconds=1),
                )
            ),
        )
    with pytest.raises(ValueError):
        build_source_assessment_projection(
            prepared,
            frozen_at=NOW,
            source_histories=source_histories,
            assertion_histories=assertion_histories,
        )


def test_origin_analysis_must_refer_to_the_exact_capture_claim_and_issuer():
    prepared = targets()
    origins = analyse_origin_chains([node()])
    with pytest.raises(ValueError, match="captured evidence"):
        build_source_assessment_projection(prepared, frozen_at=NOW, origins=origins)


def test_uncited_original_can_be_retained_in_the_origin_graph_without_becoming_claim_support():
    evidence = (*EVIDENCE, replace(EVIDENCE[0], label="E2", event_id="original-2"))
    prepared = targets(evidence=evidence)
    claim = prepared.claims[0].claim_id
    origins = analyse_origin_chains(
        [
            node(
                f"N{i}",
                evidence_id=row.capture_id,
                claim_id=claim,
                source_id=row.source_id,
                organisation=row.declared_organisation,
            )
            for i, row in enumerate(prepared.evidence, 1)
        ]
    )
    result = build_source_assessment_projection(prepared, frozen_at=NOW, origins=origins)
    assert len(result.origins.nodes) == 2 and len(result.assessments) == 1


@pytest.mark.parametrize("declared", [None, "same-parent"])
def test_origin_nodes_cannot_invent_or_split_the_frozen_organisation(declared):
    evidence = tuple(
        replace(EVIDENCE[0], label=f"E{i}", event_id=f"event-{i}", independence_key=declared or "")
        for i in (1, 2)
    )
    prepared = targets(body=ReportBody(key_judgements=(judgement("E1", "E2"),)), evidence=evidence)
    origins = analyse_origin_chains(
        [
            node(
                f"N{i}",
                evidence_id=row.capture_id,
                claim_id=prepared.claims[0].claim_id,
                source_id=row.source_id,
                organisation=f"invented-parent-{i}",
            )
            for i, row in enumerate(prepared.evidence, 1)
        ]
    )
    with pytest.raises(ValueError, match="organisation"):
        build_source_assessment_projection(prepared, frozen_at=NOW, origins=origins)


@pytest.mark.parametrize("field", ["source_histories", "assertion_histories", "authenticities"])
def test_empty_non_mapping_inputs_are_not_silently_treated_as_absent(field):
    with pytest.raises(ValueError, match="mappings"):
        build_source_assessment_projection(targets(), frozen_at=NOW, **{field: []})


@pytest.mark.parametrize("change", ["statement", "capture", "citations", "version"])
def test_saved_projection_cannot_be_reused_after_a_material_binding_changes(change):
    saved = source_assessment_report_to_dict(projection())
    body, evidence, version = BODY, EVIDENCE, VERSION
    if change == "statement":
        body = ReportBody(
            key_judgements=(replace(BODY.key_judgements[0], statement="Changed judgement."),)
        )
    elif change == "capture":
        evidence = (replace(EVIDENCE[0], title="Amended source title."),)
    elif change == "citations":
        body = ReportBody(
            key_judgements=(replace(BODY.key_judgements[0], contradicting_evidence=("E1",)),)
        )
    else:
        version = UUID("00000000-0000-4000-8000-000000000002")
    with pytest.raises(SourceAssessmentSnapshotError):
        restore_source_assessment_projection(
            saved, report_version_id=version, body=body, evidence=evidence
        )


def test_confidence_capping_does_not_change_the_underlying_claim_identity():
    body = ReportBody(key_judgements=(replace(BODY.key_judgements[0], confidence=Confidence.LOW),))
    assert targets(body=body) == targets()


def test_absent_legacy_metadata_stays_absent_and_required_metadata_cannot_silently_fall_back():
    assert (
        restore_source_assessment_projection(
            None, report_version_id=VERSION, body=BODY, evidence=EVIDENCE
        )
        is None
    )
    with pytest.raises(SourceAssessmentSnapshotError):
        restore_source_assessment_projection(
            None, report_version_id=VERSION, body=BODY, evidence=EVIDENCE, required=True
        )


def test_empty_report_remains_explicitly_without_claim_assessments():
    prepared = targets(body=ReportBody())
    report = build_source_assessment_projection(prepared, frozen_at=NOW)
    assert report.claims == report.assessments == report.origins.nodes == ()
