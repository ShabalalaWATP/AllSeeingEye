"""Selected claims retain exact revisions, original package bytes and bounded integrity."""

import hashlib
import io
import json
import zipfile
from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest

from ase.adapters.reports import claim_evidence_package as package_module
from ase.adapters.reports.claim_evidence_package import SelectedClaimPackageRenderer
from ase.adapters.reports.evidence_package import FrozenEvidencePackageRenderer
from ase.domain.claim_revisions import ClaimReviewState, revise_claim
from ase.domain.errors import InvalidRequest
from report_documents_helpers import document_records
from test_claim_revisions import revision_args


def records():
    args = revision_args()
    record, _ = document_records()
    version = args["version"]
    record = replace(record, id=version.report_id)
    initial = revise_claim(**args)
    reviewed = revise_claim(
        **{
            **args,
            "revision_id": uuid4(),
            "previous": initial,
            "statement": "The selected correction remains an attributed assertion.",
            "state": ClaimReviewState.REVIEWED,
            "reason": "Checked against the original excerpt.",
            "now": args["now"] + timedelta(minutes=1),
        }
    )
    return record, version, initial, reviewed


def files(content):
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def test_selection_preserves_original_bytes_and_all_manifest_hashes():
    record, version, initial, reviewed = records()
    original = FrozenEvidencePackageRenderer().render(record, version)
    original_files = files(original)
    renderer = SelectedClaimPackageRenderer()
    output = renderer.render(record, version, (reviewed,))
    assert output == renderer.render(record, version, (reviewed,))
    exported = files(output)
    for name, content in original_files.items():
        assert exported["original-manifest.json" if name == "manifest.json" else name] == content
    manifest = json.loads(exported["manifest.json"])
    assert manifest["schema_version"] == "ase-evidence-package-v2"
    assert manifest["base_package_sha256"] == hashlib.sha256(original).hexdigest()
    assert manifest["selected_revision_ids"] == [str(reviewed.id)]
    for item in manifest["files"]:
        content = exported[item["path"]]
        assert item["bytes"] == len(content)
        assert item["sha256"] == hashlib.sha256(content).hexdigest()
    selected = json.loads(exported["claim-revisions.json"])["revisions"]
    assert len(selected) == 1 and selected[0]["id"] == str(reviewed.id)
    assert selected[0]["previous_id"] == str(initial.id)
    assert selected[0]["citations"][0]["excerpt"]["text"] == "中国项目"
    assert initial.statement not in exported["claim-revisions.json"].decode("utf-8")
    assert reviewed.statement not in exported["report.json"].decode("utf-8")


@pytest.mark.parametrize("fault", ["empty", "duplicate", "too_many", "other_version", "excerpt"])
def test_invalid_selection_never_produces_an_export(fault):
    record, version, initial, reviewed = records()
    selection = (reviewed,)
    if fault == "empty":
        selection = ()
    elif fault == "duplicate":
        selection = (reviewed, reviewed)
    elif fault == "too_many":
        selection = tuple(replace(initial, id=uuid4()) for _ in range(21))
    elif fault == "other_version":
        selection = (replace(reviewed, report_version_id=uuid4()),)
    else:
        version = replace(
            version, evidence=(replace(version.evidence[0], title="Different source"),)
        )
    with pytest.raises(InvalidRequest):
        SelectedClaimPackageRenderer().render(record, version, selection)


def test_aggregate_size_limit_rejects_without_truncating(monkeypatch):
    record, version, initial, _ = records()
    monkeypatch.setattr(package_module, "MAX_PACKAGE_BYTES", 100)
    with pytest.raises(InvalidRequest, match="limit"):
        SelectedClaimPackageRenderer().render(record, version, (initial,))


def test_selection_can_include_distinct_historical_revisions():
    record, version, initial, reviewed = records()
    output = SelectedClaimPackageRenderer().render(record, version, (initial, reviewed))
    selected = json.loads(files(output)["claim-revisions.json"])["revisions"]
    assert [item["id"] for item in selected] == [str(initial.id), str(reviewed.id)]


def test_valid_base_can_exhaust_remaining_budget_when_claims_are_added(monkeypatch):
    record, version, initial, _ = records()
    base = FrozenEvidencePackageRenderer().render(record, version)
    base_size = sum(len(content) for content in files(base).values())
    monkeypatch.setattr(package_module, "MAX_PACKAGE_BYTES", base_size + 1)
    with pytest.raises(InvalidRequest, match="limit"):
        SelectedClaimPackageRenderer().render(record, version, (initial,))
