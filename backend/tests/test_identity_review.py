"""Operator identity review preserves source namespaces and frozen report history."""

from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest

from ase.domain.claim_revisions import ClaimCitationInput, ClaimRelation
from ase.domain.identity_review import (
    IdentityDisposition,
    freeze_identity_candidate,
    revise_identity_decision,
)
from ase.domain.research_context import CapturedIdentityValue, build_research_context
from report_documents_helpers import document_records
from test_research_context import attrs, item


def arguments():
    _, version = document_records(uuid4())
    evidence = item(
        attributes=attrs(
            lei="12345678901234567890",
            legal_name="中国公司 / شرکت / Компания",
            reported_registration_number="000123",
            reported_jurisdiction="CN",
        )
    )
    version.evidence = (evidence,)
    version.research_context = build_research_context(version.evidence)
    return {
        "version": version,
        "revision_id": uuid4(),
        "decision_id": uuid4(),
        "previous": None,
        "subject": "Does this record identify the organisation named in the report?",
        "candidate_label": "E1",
        "disposition": IdentityDisposition.UNRESOLVED,
        "rationale": "The registry identity requires further supporting records.",
        "unresolved_conflicts": ("English trading name is ambiguous.",),
        "citations": (),
        "actor_id": uuid4(),
        "now": version.created_at,
    }


def test_snapshot_keeps_original_namespaces_leading_zeroes_and_untranslated_names():
    args = arguments()
    before = args["version"].research_context
    review = revise_identity_decision(**args)
    captured = {row.key: row.value for row in review.candidate.attributes}
    assert captured["reported_registration_number"] == "000123"
    assert captured["reported_jurisdiction"] == "CN"
    assert captured["legal_name"] == "中国公司 / شرکت / Компания"
    assert review.candidate.candidate.identifiers[0].namespace == "lei"
    assert args["version"].research_context == before
    assert before.identity_candidates[0].status == "unverified_candidate"


def test_correction_appends_disposition_and_preserves_the_original_decision():
    args = arguments()
    first = revise_identity_decision(**args)
    second = revise_identity_decision(
        **{
            **args,
            "revision_id": uuid4(),
            "previous": first,
            "disposition": IdentityDisposition.REJECTED,
            "rationale": "The registration belongs to a different organisation.",
        }
    )
    assert first.disposition is IdentityDisposition.UNRESOLVED
    assert second.disposition is IdentityDisposition.REJECTED
    assert second.previous_id == first.id and second.number == 2
    assert second.candidate == first.candidate


@pytest.mark.parametrize("change", ["subject", "candidate", "version", "time"])
def test_corrections_reject_changed_anchors(change):
    args = arguments()
    first = revise_identity_decision(**args)
    args.update(previous=first, revision_id=uuid4())
    if change == "subject":
        args["subject"] = "Another organisation"
    elif change == "candidate":
        version = args["version"]
        version.evidence = (replace(version.evidence[0], attributes=attrs(lei="other")),)
    elif change == "version":
        args["version"] = replace(args["version"], id=uuid4())
    else:
        args["now"] -= timedelta(seconds=1)
    with pytest.raises(ValueError):
        revise_identity_decision(**args)


def test_equal_registration_strings_in_different_jurisdictions_stay_distinct():
    args = arguments()
    version = args["version"]
    first = freeze_identity_candidate(version, "E1")
    version.evidence = (
        replace(
            version.evidence[0],
            attributes=attrs(
                lei="12345678901234567890",
                reported_registration_number="000123",
                reported_jurisdiction="GB",
            ),
        ),
    )
    second = freeze_identity_candidate(version, "E1")
    assert first != second


@pytest.mark.parametrize("change", ["unknown", "duplicate", "absent", "withdrawn", "rationale"])
def test_invalid_review_input_is_rejected(change):
    args = arguments()
    if change == "unknown":
        args["candidate_label"] = "E2"
    elif change == "duplicate":
        args["version"].evidence *= 2
    elif change == "absent":
        args["version"].research_context = None
    elif change == "withdrawn":
        args["disposition"] = IdentityDisposition.WITHDRAWN
    else:
        args["rationale"] = " "
    with pytest.raises(ValueError):
        revise_identity_decision(**args)


def test_optional_exact_citations_reject_fabricated_excerpt():
    args = arguments()
    text = args["version"].evidence[0].title
    citation = ClaimCitationInput("E1", ClaimRelation.CONTEXT, "title", 0, len(text), text)
    args["citations"] = (citation,)
    review = revise_identity_decision(**args)
    assert review.citations[0].excerpt.text == text
    args["citations"] = (replace(citation, text="Invented"),)
    with pytest.raises(ValueError):
        revise_identity_decision(**args)


@pytest.mark.parametrize(
    "field,value",
    [
        ("number", 0),
        ("number", True),
        ("number", 101),
        ("previous_id", "not-a-uuid"),
        ("disposition", "matched"),
        ("unresolved_conflicts", []),
        ("citations", []),
    ],
)
def test_malformed_previous_revisions_cannot_seed_correction_history(field, value):
    args = arguments()
    first = revise_identity_decision(**args)
    args.update(previous=replace(first, **{field: value}), revision_id=uuid4())
    with pytest.raises(ValueError):
        revise_identity_decision(**args)


@pytest.mark.parametrize("field", ["attributes", "identifiers", "aliases", "forged", "method"])
def test_mutable_or_fabricated_candidate_snapshots_are_rejected(field):
    args = arguments()
    version = args["version"]
    context = version.research_context
    candidate = context.identity_candidates[0]
    if field == "attributes":
        version.evidence = (
            replace(version.evidence[0], attributes=list(version.evidence[0].attributes)),
        )
    elif field == "method":
        version.research_context = replace(context, method_version="unknown-v2")
    else:
        values = (CapturedIdentityValue("lei", "fabricated"),) if field == "forged" else []
        changed = replace(candidate, **{("identifiers" if field == "forged" else field): values})
        version.research_context = replace(context, identity_candidates=(changed,))
    with pytest.raises(ValueError):
        revise_identity_decision(**args)


def test_declared_identity_match_must_equal_the_captured_attribute():
    args = arguments()
    version = args["version"]
    version.evidence = (
        replace(
            version.evidence[0],
            attributes=attrs(
                company_number="000123",
                identity_match="exact_requested_identifier",
            ),
        ),
    )
    version.research_context = build_research_context(version.evidence)
    assert (
        revise_identity_decision(**args).candidate.candidate.declared_match_status
        == "exact_requested_identifier"
    )
