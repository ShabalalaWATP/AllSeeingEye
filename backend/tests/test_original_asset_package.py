"""Selected original archives preserve base bytes and reject corrupt exports."""

import hashlib
import json
from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from ase.adapters.reports.claim_evidence_package import SelectedClaimPackageRenderer
from ase.adapters.reports.evidence_package import FrozenEvidencePackageRenderer
from ase.api.schemas_claim_export import ClaimPackageIn
from ase.domain.errors import InvalidRequest
from ase.domain.original_assets import OriginalAsset, OriginalAssetContent
from report_documents_helpers import document_records
from test_selected_claim_package import files


def original(record, version, content=b"original source bytes"):
    return OriginalAssetContent(
        OriginalAsset(
            id=uuid4(),
            report_id=record.id,
            report_version_id=version.id,
            version_number=version.number,
            evidence_label="E1",
            source_id="research_import",
            event_id="upload",
            sha256=hashlib.sha256(content).hexdigest(),
            byte_count=len(content),
            filename="../../danger.html",
            media_type="text/html",
            permitted_use="Own material",
            owner_id=record.created_by,
            team_id=record.team_id,
            uploader_id=record.created_by,
            created_at=version.created_at,
            expires_at=version.created_at + timedelta(days=30),
            reservation_expires_at=version.created_at,
            status="active",
        ),
        content,
    )


def test_original_only_preserves_base_and_uses_generated_paths():
    record, version = document_records()
    selected = original(record, version)
    base = FrozenEvidencePackageRenderer().render(record, version)
    renderer = SelectedClaimPackageRenderer()
    package = renderer.render(record, version, (), original_assets=(selected,))
    assert package == renderer.render(record, version, (), original_assets=(selected,))
    packed = files(package)
    for name, data in files(base).items():
        assert packed["original-manifest.json" if name == "manifest.json" else name] == data
    manifest = json.loads(packed["manifest.json"])
    assert manifest["schema_version"] == "ase-evidence-package-v4"
    assert manifest["original_assets_included"] is True
    assert manifest["selected_asset_ids"] == [str(selected.asset.id)]
    assert manifest["base_package_sha256"] == hashlib.sha256(base).hexdigest()
    assert packed[f"originals/{selected.asset.id}.bin"] == selected.content
    assert selected.asset.filename not in packed
    assert b"session_family_id" not in packed["original-assets.json"]
    for row in manifest["files"]:
        assert row["bytes"] == len(packed[row["path"]])
        assert row["sha256"] == hashlib.sha256(packed[row["path"]]).hexdigest()


@pytest.mark.parametrize("change", ["hash", "version", "status", "length", "duplicate"])
def test_original_renderer_rejects_corruption_or_wrong_selection(change):
    record, version = document_records()
    selected = original(record, version)
    changes = {
        "hash": {"sha256": "0" * 64},
        "version": {"report_version_id": uuid4()},
        "status": {"status": "deleted"},
        "length": {"byte_count": 1},
    }
    rows = (
        (selected, selected)
        if change == "duplicate"
        else (replace(selected, asset=replace(selected.asset, **changes[change])),)
    )
    with pytest.raises(InvalidRequest):
        SelectedClaimPackageRenderer().render(record, version, (), original_assets=rows)


def test_original_budget_does_not_silently_omit_any_member():
    record, version = document_records()
    rows = tuple(original(record, version, b"a" * (8 * 1024 * 1024)) for _ in range(4))
    with pytest.raises(InvalidRequest, match="24 MiB"):
        SelectedClaimPackageRenderer().render(record, version, (), original_assets=rows)


def test_selection_schema_counts_all_categories_and_rejects_duplicate_assets():
    asset = uuid4()
    assert ClaimPackageIn(version_number=1, asset_ids=[asset]).asset_ids == [asset]
    for payload in (
        {"asset_ids": [asset, asset]},
        {"asset_ids": []},
        {
            "asset_ids": [uuid4() for _ in range(20)],
            "revisions": [{"claim_id": uuid4(), "revision_id": uuid4()}],
        },
    ):
        with pytest.raises(ValidationError):
            ClaimPackageIn(version_number=1, **payload)
