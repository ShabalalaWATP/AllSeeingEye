"""Source-specific immutable relationship assertions and attributed corrections."""

import json
from dataclasses import replace
from uuid import uuid4

import pytest

from ase.domain.claim_revisions import ClaimCitationInput, ClaimRelation
from ase.domain.evidence_attributes import EvidenceAttribute
from ase.domain.relationship_assertions import freeze_relationship_assertion
from ase.domain.relationship_review import RelationshipDisposition, revise_relationship_review
from report_documents_helpers import document_records

CHILD = "5493001KJTIIGC8Y1R12"
PARENT = "529900T8BM49AURSDO55"


def arguments():
    _, version = document_records()
    attributes = {
        "child_lei": CHILD,
        "parent_lei": PARENT,
        "record_kind": "reported_accounting_consolidation",
        "reported_relationship_type": "IS_DIRECTLY_CONSOLIDATED_BY",
        "reported_relationship_status": "ACTIVE",
        "reported_periods": json.dumps(
            [{"type": "ACCOUNTING_PERIOD", "startDate": "2020-01-01", "endDate": "2020-12-31"}]
        ),
        "reported_periods_omitted": 0,
        "reported_valid_from": "2020-05-01",
        "reported_valid_to": "",
    }
    evidence = replace(
        version.evidence[0],
        source_id="research-gleif-direct-parent",
        attributes=tuple(EvidenceAttribute(key, value) for key, value in attributes.items()),
    )
    version = replace(version, evidence=(evidence, *version.evidence[1:]))
    return {
        "version": version,
        "revision_id": uuid4(),
        "relationship_id": uuid4(),
        "previous": None,
        "evidence_label": evidence.label,
        "disposition": RelationshipDisposition.UNRESOLVED,
        "rationale": "The captured accounting assertion needs corroboration.",
        "unresolved_conflicts": (),
        "citations": (),
        "actor_id": uuid4(),
        "now": version.created_at,
    }


def test_supported_relationship_retains_dates_and_never_infers_current_validity():
    values = arguments()
    first = revise_relationship_review(**values)
    assert first.assertion.child_lei == CHILD and first.assertion.parent_lei == PARENT
    assert first.assertion.periods[0].startDate == "2020-01-01"
    assert not hasattr(first.assertion, "currently_valid")
    second = revise_relationship_review(
        **{
            **values,
            "revision_id": uuid4(),
            "previous": first,
            "disposition": RelationshipDisposition.DISPUTED,
            "rationale": "Contrary reporting exists.",
        }
    )
    assert second.assertion == first.assertion and second.previous_id == first.id
    assert first.disposition is RelationshipDisposition.UNRESOLVED


@pytest.mark.parametrize("change", ["source", "kind", "lei", "duplicate", "missing"])
def test_unsupported_or_ambiguous_assertions_cannot_be_reviewed(change):
    values = arguments()
    version = values["version"]
    item = version.evidence[0]
    attributes = list(item.attributes)
    if change == "source":
        item = replace(item, source_id="unrecognised-source")
    elif change == "duplicate":
        attributes.append(attributes[0])
    elif change == "missing":
        attributes = attributes[1:]
    else:
        key = "child_lei" if change == "lei" else "reported_relationship_type"
        attributes = [
            replace(row, value="invalid") if row.key == key else row for row in attributes
        ]
    item = replace(item, attributes=tuple(attributes))
    with pytest.raises(ValueError):
        freeze_relationship_assertion(replace(version, evidence=(item,)), item.label)


@pytest.mark.parametrize(
    "raw,state",
    [
        (None, "missing"),
        ("truncated...", "unavailable"),
        ('[{"type":"A","type":"B","startDate":"","endDate":""}]', "unavailable"),
        ("[]", "parsed"),
    ],
)
def test_incomplete_periods_preserve_raw_metadata_without_invented_dates(raw, state):
    version = arguments()["version"]
    item = version.evidence[0]
    attributes = tuple(row for row in item.attributes if row.key != "reported_periods")
    if raw is not None:
        attributes += (EvidenceAttribute("reported_periods", raw),)
    item = replace(item, attributes=attributes)
    snapshot = freeze_relationship_assertion(replace(version, evidence=(item,)), item.label)
    assert snapshot.periods_state == state and snapshot.attributes == attributes


def test_initial_withdrawal_and_endpoint_mutation_are_rejected():
    values = arguments()
    with pytest.raises(ValueError, match="initial"):
        revise_relationship_review(**{**values, "disposition": RelationshipDisposition.WITHDRAWN})
    first = revise_relationship_review(**values)
    with pytest.raises(ValueError, match="anchors"):
        revise_relationship_review(
            **{
                **values,
                "previous": first,
                "revision_id": uuid4(),
                "version": replace(values["version"], id=uuid4()),
            }
        )


def test_ultimate_source_retains_its_distinct_type_and_truncation_notice():
    version = arguments()["version"]
    item = version.evidence[0]
    attributes = tuple(
        replace(row, value="IS_ULTIMATELY_CONSOLIDATED_BY")
        if row.key == "reported_relationship_type"
        else replace(row, value=3)
        if row.key == "reported_periods_omitted"
        else row
        for row in item.attributes
    )
    item = replace(item, source_id="research-gleif-ultimate-parent", attributes=attributes)
    snapshot = freeze_relationship_assertion(replace(version, evidence=(item,)), item.label)
    assert snapshot.kind == "ultimate"
    assert snapshot.relationship_type == "IS_ULTIMATELY_CONSOLIDATED_BY"
    assert snapshot.periods_state == "parsed"
    assert {row.key: row.value for row in snapshot.attributes}["reported_periods_omitted"] == 3


def test_revision_cap_and_exact_excerpt_tampering_are_rejected():
    values = arguments()
    first = revise_relationship_review(**values)
    last = replace(first, id=uuid4(), number=100, previous_id=uuid4())
    with pytest.raises(ValueError, match="revision number"):
        revise_relationship_review(**{**values, "revision_id": uuid4(), "previous": last})
    with pytest.raises(ValueError):
        revise_relationship_review(
            **{
                **values,
                "citations": (
                    ClaimCitationInput("E1", ClaimRelation.OPPOSING, "title", 0, 6, "forged"),
                ),
            }
        )
