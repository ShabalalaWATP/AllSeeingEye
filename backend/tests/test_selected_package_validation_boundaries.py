"""Offline package selections retain immutable citation anchors and bounded inputs."""

from dataclasses import replace
from uuid import uuid4

import pytest

from ase.adapters.reports.identity_package_validation import validate_identity_selection
from ase.adapters.reports.relationship_package_validation import validate_relationship_selection
from ase.domain.claim_revisions import ClaimCitationInput, ClaimRelation, freeze_claim_citations
from ase.domain.errors import InvalidRequest
from test_selected_identity_package import records as identity_records
from test_selected_relationship_package import records as relationship_records


@pytest.mark.parametrize(
    "factory,validate",
    [
        (identity_records, validate_identity_selection),
        (relationship_records, validate_relationship_selection),
    ],
)
def test_selection_type_count_and_citation_integrity_are_enforced(factory, validate):
    record, version, first, _ = factory()
    for selected in ([first], tuple(replace(first, id=uuid4()) for _ in range(21))):
        with pytest.raises(InvalidRequest, match="twenty"):
            validate(record, version, selected)
    item = version.evidence[0]
    citation = ClaimCitationInput(
        item.label, ClaimRelation.SUPPORTING, "title", 0, len(item.title), item.title
    )
    frozen = freeze_claim_citations(version, (citation,))
    validate(record, version, (replace(first, citations=frozen),))
    tampered = replace(frozen[0], event_id="a-different-captured-event")
    with pytest.raises(InvalidRequest, match="frozen report evidence"):
        validate(record, version, (replace(first, citations=(tampered,)),))


def test_relationship_selection_requires_its_actual_parent_report():
    record, version, first, _ = relationship_records()
    record.id = uuid4()
    with pytest.raises(InvalidRequest, match="parent report"):
        validate_relationship_selection(record, version, (first,))
