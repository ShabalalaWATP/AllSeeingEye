"""Claim annotations cannot rewrite evidence or silently move between report versions."""

from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest

from ase.domain.claim_revisions import (
    ClaimCitationInput,
    ClaimKind,
    ClaimRelation,
    ClaimReviewState,
    freeze_claim_citations,
    revise_claim,
)
from report_documents_helpers import document_records


def inputs():
    _, version = document_records()
    evidence = replace(version.evidence[0], title="中国项目于2011年获批。", summary=None)
    version = replace(version, evidence=(evidence,))
    citation = ClaimCitationInput(
        evidence.label, ClaimRelation.SUPPORTING, "title", 0, 4, "中国项目"
    )
    return version, citation


def revision_args():
    version, citation = inputs()
    return {
        "version": version,
        "revision_id": uuid4(),
        "claim_id": uuid4(),
        "previous": None,
        "statement": "The source reports project approval in 2011.",
        "kind": ClaimKind.REPORTED_FACT,
        "state": ClaimReviewState.PROPOSED,
        "citations": (citation,),
        "unresolved_conflicts": (),
        "reason": "Record the attributed assertion.",
        "actor_id": uuid4(),
        "now": version.created_at,
    }


def test_unicode_locator_and_original_identity_are_frozen():
    version, citation = inputs()
    frozen = freeze_claim_citations(version, (citation,))[0]
    assert frozen.excerpt.text == "中国项目"
    assert frozen.excerpt.start == 0 and frozen.excerpt.end == 4
    assert len(frozen.excerpt.sha256) == 64
    assert frozen.event_id == version.evidence[0].event_id
    assert frozen.source_content_hash == version.evidence[0].content_hash
    assert version.evidence[0].summary is None


@pytest.mark.parametrize(
    "changes",
    [
        {"label": "E999"},
        {"field": "title_en"},
        {"field": "summary"},
        {"start": -1},
        {"start": True},
        {"end": False},
        {"end": 10000},
        {"text": "Chinese project"},
        {"relation": "supporting"},
        {"end": 0},
    ],
)
def test_bad_or_translated_excerpt_is_rejected(changes):
    version, citation = inputs()
    with pytest.raises(ValueError):
        freeze_claim_citations(version, (replace(citation, **changes),))


@pytest.mark.parametrize("count", [0, 2, 21])
def test_empty_duplicate_or_excessive_citations_are_rejected(count):
    version, citation = inputs()
    with pytest.raises(ValueError):
        freeze_claim_citations(version, (citation,) * count)


def test_opposition_is_explicit_and_does_not_change_source_grade():
    version, citation = inputs()
    original = version.evidence[0]
    sources = freeze_claim_citations(
        version,
        (
            citation,
            replace(citation, relation=ClaimRelation.OPPOSING),
        ),
    )
    assert [row.relation for row in sources] == [ClaimRelation.SUPPORTING, ClaimRelation.OPPOSING]
    assert version.evidence[0] is original


def test_correction_preserves_previous_and_does_not_mutate_report():
    args = revision_args()
    original_body = args["version"].body
    initial = revise_claim(**args)
    reviewed = revise_claim(
        **{
            **args,
            "previous": initial,
            "revision_id": uuid4(),
            "state": ClaimReviewState.REVIEWED,
            "reason": "Checked attribution and date.",
            "unresolved_conflicts": ("Completion date remains disputed.",),
        }
    )
    assert initial.number == 1 and initial.state is ClaimReviewState.PROPOSED
    assert reviewed.previous_id == initial.id and reviewed.number == 2
    assert reviewed.claim_id == initial.claim_id
    assert reviewed.unresolved_conflicts == ("Completion date remains disputed.",)
    assert args["version"].body is original_body


@pytest.mark.parametrize("change", ["claim", "report", "version", "id", "time"])
def test_correction_cannot_retarget_or_reorder_history(change):
    args = revision_args()
    initial = revise_claim(**args)
    args.update(previous=initial, revision_id=uuid4())
    if change == "claim":
        args["claim_id"] = uuid4()
    elif change == "report":
        args["version"] = replace(args["version"], report_id=uuid4())
    elif change == "version":
        args["version"] = replace(args["version"], id=uuid4())
    elif change == "id":
        args["revision_id"] = initial.id
    else:
        args["now"] -= timedelta(seconds=1)
    with pytest.raises(ValueError):
        revise_claim(**args)


@pytest.mark.parametrize(
    "changes",
    [
        {"state": ClaimReviewState.REVIEWED},
        {"state": ClaimReviewState.WITHDRAWN},
        {"statement": " "},
        {"reason": ""},
        {"unresolved_conflicts": ("",)},
        {"unresolved_conflicts": ("x",) * 21},
        {"statement": "x" * 1201},
        {"kind": "reported_fact"},
    ],
)
def test_initial_claim_requires_bounded_proposal_and_reason(changes):
    with pytest.raises(ValueError):
        revise_claim(**{**revision_args(), **changes})


def test_naive_audit_time_rejected():
    args = revision_args()
    args["now"] = args["now"].replace(tzinfo=None)
    with pytest.raises(ValueError):
        revise_claim(**args)


def test_offsets_are_unicode_code_points_not_utf16_units():
    version, citation = inputs()
    version = replace(version, evidence=(replace(version.evidence[0], title="🛰中国项目"),))
    valid = replace(citation, start=1, end=5)
    assert freeze_claim_citations(version, (valid,))[0].excerpt.text == "中国项目"
    with pytest.raises(ValueError):
        freeze_claim_citations(version, (replace(valid, start=2, end=6),))


def test_conflicts_are_defensively_frozen():
    conflicts = ["Unconfirmed completion date."]
    revised = revise_claim(**{**revision_args(), "unresolved_conflicts": conflicts})
    conflicts.append("Later modification")
    assert revised.unresolved_conflicts == ("Unconfirmed completion date.",)


@pytest.mark.parametrize("field", ["statement", "reason", "unresolved_conflicts"])
@pytest.mark.parametrize("invalid", ["bad\ud800text", "bad\x00text"])
def test_unencodable_text_and_controls_rejected(field, invalid):
    value = (invalid,) if field == "unresolved_conflicts" else invalid
    with pytest.raises(ValueError):
        revise_claim(**{**revision_args(), field: value})
