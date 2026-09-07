"""Strict original-byte eligibility, without substituting extracted or thumbnail hashes."""

import re

from ase.domain.errors import InvalidRequest
from ase.domain.evidence import EvidenceItem
from ase.domain.evidence_attributes import evidence_attributes_to_list
from ase.domain.original_assets import MAX_ASSET_BYTES, OriginalAssetRequest
from ase.domain.report_records import ReportVersion


def plain_text(value: str, maximum: int) -> bool:
    return (
        isinstance(value, str)
        and bool(value.strip())
        and len(value) <= maximum
        and not any(ord(char) < 32 or ord(char) == 127 for char in value)
    )


def original_anchor(version: ReportVersion, label: str) -> tuple[EvidenceItem, str, str, str]:
    matches = [item for item in version.evidence if item.label == label]
    if len(matches) != 1:
        raise InvalidRequest("Choose one exact frozen evidence label.")
    item = matches[0]
    if item.source_id not in {"research_import", "research_media"}:
        raise InvalidRequest("Original retention requires internal document or media evidence.")
    try:
        evidence_attributes_to_list(item.attributes)
    except ValueError:
        raise InvalidRequest(
            "The frozen original attributes are malformed or duplicated."
        ) from None
    attributes = {row.key: row.value for row in item.attributes}
    digest, filename, media_type = (
        attributes.get("original_sha256"),
        attributes.get("filename"),
        attributes.get("media_type"),
    )
    if (
        not isinstance(digest, str)
        or re.fullmatch(r"[0-9a-f]{64}", digest) is None
        or not isinstance(filename, str)
        or not plain_text(filename, 120)
        or any(char in filename for char in "/\\:")
        or not isinstance(media_type, str)
        or re.fullmatch(r"[a-z0-9][a-z0-9.+-]*/[a-z0-9][a-z0-9.+-]*", media_type) is None
        or len(media_type) > 160
        or not plain_text(item.event_id, 200)
    ):
        raise InvalidRequest("The frozen evidence has no valid original-byte anchor.")
    return item, digest, filename, media_type


def validate_request(request: OriginalAssetRequest) -> None:
    if (
        type(request.byte_count) is not int
        or not 1 <= request.byte_count <= MAX_ASSET_BYTES
        or type(request.retention_days) is not int
        or not 1 <= request.retention_days <= 90
        or type(request.version_number) is not int
        or request.version_number < 1
        or not plain_text(request.evidence_label, 40)
        or not plain_text(request.filename, 120)
        or any(char in request.filename for char in "/\\:")
        or not plain_text(request.media_type, 160)
        or not plain_text(request.permitted_use, 1000)
    ):
        raise InvalidRequest("Provide bounded original metadata, 1 byte to 8 MiB and 1-90 days.")
