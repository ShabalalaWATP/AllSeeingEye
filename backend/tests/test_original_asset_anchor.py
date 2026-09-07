"""Original anchors never fall back to document text hashes or sampled media hashes."""

from dataclasses import replace

import pytest

from ase.application.reports.original_asset_anchor import original_anchor
from ase.domain.errors import InvalidRequest
from ase.domain.evidence_attributes import EvidenceAttribute
from report_documents_helpers import document_records


def anchored(**changes):
    _, version = document_records()
    item = replace(
        version.evidence[0],
        source_id="research_import",
        attributes=(
            EvidenceAttribute("original_sha256", "a" * 64),
            EvidenceAttribute("filename", "original.txt"),
            EvidenceAttribute("media_type", "text/plain"),
        ),
    )
    return replace(version, evidence=(replace(item, **changes),))


@pytest.mark.parametrize("source_id", ["research_import", "research_media"])
def test_only_frozen_internal_original_digest_is_selected(source_id):
    item, digest, filename, media_type = original_anchor(anchored(source_id=source_id), "E1")
    assert digest == "a" * 64 and digest != item.content_hash
    assert filename == "original.txt" and media_type == "text/plain"


@pytest.mark.parametrize(
    "attributes",
    [
        (EvidenceAttribute("sample_sha256", "a" * 64),),
        (EvidenceAttribute("content_hash", "a" * 64),),
        (
            EvidenceAttribute("original_sha256", "a" * 64),
            EvidenceAttribute("original_sha256", "a" * 64),
        ),
        (EvidenceAttribute("original_sha256", True),),
        (EvidenceAttribute("original_sha256", "A" * 64),),
        (EvidenceAttribute("original_sha256", "a" * 63),),
    ],
)
def test_missing_malformed_or_duplicated_original_digest_rejected(attributes):
    with pytest.raises(InvalidRequest):
        original_anchor(anchored(attributes=attributes), "E1")


def test_duplicate_label_foreign_source_and_unsafe_frozen_metadata_rejected():
    version = anchored()
    for invalid in (
        replace(version, evidence=version.evidence * 2),
        anchored(source_id="news"),
        anchored(attributes=(*version.evidence[0].attributes, EvidenceAttribute("filename", "x"))),
        anchored(
            attributes=tuple(
                EvidenceAttribute(row.key, "../../file" if row.key == "filename" else row.value)
                for row in version.evidence[0].attributes
            )
        ),
    ):
        with pytest.raises(InvalidRequest):
            original_anchor(invalid, "E1")
