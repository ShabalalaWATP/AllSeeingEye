"""Exact relationship revisions extend packages without rewriting original evidence."""

import hashlib
import json
from dataclasses import replace
from uuid import uuid4

import pytest

from ase.adapters.reports.claim_evidence_package import SelectedClaimPackageRenderer
from ase.adapters.reports.evidence_package import FrozenEvidencePackageRenderer
from ase.domain.claim_revisions import (
    ClaimCitationInput,
    ClaimKind,
    ClaimRelation,
    ClaimReviewState,
    revise_claim,
)
from ase.domain.errors import InvalidRequest
from ase.domain.relationship_review import RelationshipDisposition, revise_relationship_review
from report_documents_helpers import document_records
from test_relationship_review import arguments
from test_selected_claim_package import files


def records():
    args = arguments()
    record, _ = document_records()
    version = args["version"]
    record.id = version.report_id
    record.scope = {"research_focus": "general"}
    first = revise_relationship_review(**args)
    second = revise_relationship_review(
        **{
            **args,
            "revision_id": uuid4(),
            "previous": first,
            "disposition": RelationshipDisposition.DISPUTED,
            "rationale": "A different registry entry.",
        }
    )
    return record, version, first, second


def test_relationship_only_package_preserves_base_bytes_and_exact_selected_history():
    record, version, first, second = records()
    base = FrozenEvidencePackageRenderer().render(record, version)
    renderer = SelectedClaimPackageRenderer()
    packed = renderer.render(record, version, (), relationship_revisions=(second,))
    assert packed == renderer.render(record, version, (), relationship_revisions=(second,))
    exported = files(packed)
    for name, data in files(base).items():
        assert exported["original-manifest.json" if name == "manifest.json" else name] == data
    manifest = json.loads(exported["manifest.json"])
    assert manifest["schema_version"] == "ase-evidence-package-relationships-v1"
    assert manifest["selected_revision_ids"] == []
    assert manifest["selected_relationship_revision_ids"] == [str(second.id)]
    assert manifest["base_package_sha256"] == hashlib.sha256(base).hexdigest()
    assert not manifest["original_assets_included"]
    for row in manifest["files"]:
        assert row["bytes"] == len(exported[row["path"]])
        assert row["sha256"] == hashlib.sha256(exported[row["path"]]).hexdigest()
    selected = json.loads(exported["relationship-revisions.json"])["revisions"]
    assert len(selected) == 1 and selected[0]["id"] == str(second.id)
    assert selected[0]["previous_id"] == str(first.id)
    attributes = {row["key"]: row["value"] for row in selected[0]["assertion"]["attributes"]}
    assert attributes["reported_valid_from"] == "2020-05-01"
    assert attributes["reported_relationship_type"] == "IS_DIRECTLY_CONSOLIDATED_BY"
    assert first.rationale not in exported["relationship-revisions.json"].decode()
    assert b"No current validity is inferred" in exported["RELATIONSHIPS-README.txt"]


def test_mixed_claim_and_relationship_selection_keeps_distinct_revision_lists():
    record, version, _, second = records()
    item = version.evidence[0]
    claim = revise_claim(
        version=version,
        revision_id=uuid4(),
        claim_id=uuid4(),
        previous=None,
        statement="The source declares a registration.",
        kind=ClaimKind.REPORTED_FACT,
        state=ClaimReviewState.PROPOSED,
        citations=(
            ClaimCitationInput(
                item.label, ClaimRelation.SUPPORTING, "title", 0, len(item.title), item.title
            ),
        ),
        unresolved_conflicts=(),
        reason="Capture the attributed statement.",
        actor_id=uuid4(),
        now=version.created_at,
    )
    exported = files(
        SelectedClaimPackageRenderer().render(
            record, version, (claim,), relationship_revisions=(second,)
        )
    )
    manifest = json.loads(exported["manifest.json"])
    assert manifest["selected_revision_ids"] == [str(claim.id)]
    assert manifest["selected_relationship_revision_ids"] == [str(second.id)]
    assert json.loads(exported["claim-revisions.json"])["revisions"][0]["id"] == str(claim.id)
    with pytest.raises(InvalidRequest, match="twenty"):
        SelectedClaimPackageRenderer().render(
            record,
            version,
            (claim,),
            relationship_revisions=tuple(replace(second, id=uuid4()) for _ in range(20)),
        )


@pytest.mark.parametrize(
    "fault", ["duplicate", "endpoint", "version", "assertion", "attributes", "scope"]
)
def test_invalid_relationship_selection_is_refused_before_export(fault):
    record, version, _, second = records()
    selected = (second,)
    if fault == "duplicate":
        selected = (second, second)
    elif fault == "endpoint":
        selected = (replace(second, assertion=replace(second.assertion, parent_lei="A" * 20)),)
    elif fault == "version":
        selected = (replace(second, report_version_id=uuid4()),)
    elif fault == "assertion":
        selected = (replace(second, assertion=replace(second.assertion, source_id="other")),)
    elif fault == "attributes":
        selected = (replace(second, assertion=replace(second.assertion, attributes=())),)
    else:
        record.id = uuid4()
    with pytest.raises(InvalidRequest):
        SelectedClaimPackageRenderer().render(record, version, (), relationship_revisions=selected)
