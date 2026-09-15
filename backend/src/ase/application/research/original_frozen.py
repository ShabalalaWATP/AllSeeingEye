"""Bounded selected-original snapshot for a future authorised report-version write.

The snapshot carries exact provenance and selected parser excerpts, never raw document
bytes. Decode validates hashes, offsets, scope and retention before a historical
passage can be reopened under current access and source policy.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, fields, replace
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from ase.application.research.original_passages import (
    MAX_EXCERPT_BYTES,
    MAX_PASSAGE_CHARACTERS,
    MAX_PASSAGES,
    OriginalDocumentVersion,
    OriginalPassage,
)
from ase.application.research.original_policy import (
    MAX_ORIGINAL_BYTES,
    MAX_RETENTION_DAYS,
    MEDIA_EXTENSIONS,
    public_origin,
)
from ase.domain.research_brief_values import stable_id

FROZEN_ORIGINAL_VERSION = 1
_DOCUMENT_KEYS = frozenset(field.name for field in fields(OriginalDocumentVersion))
_PASSAGE_KEYS = frozenset(field.name for field in fields(OriginalPassage))
_DATES = ("retrieved_at", "published_at", "http_last_modified_at", "expires_at")
_HEX = re.compile(r"[0-9a-f]{64}\Z")


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _date(value: object, *, optional: bool = False) -> datetime | None:
    if value is None and optional:
        return None
    if type(value) is not str or len(value) > 48:
        raise ValueError("Invalid frozen original timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise ValueError("Invalid frozen original timestamp") from None
    if parsed.utcoffset() is None:
        raise ValueError("Frozen original timestamps must be timezone-aware")
    return parsed


def _valid_text(value: object, maximum: int) -> bool:
    return (
        type(value) is str
        and 1 <= len(value) <= maximum
        and bool(value.strip())
        and not any(ord(character) < 32 for character in value)
    )


def _validate(document: OriginalDocumentVersion) -> None:
    expected_id = _digest(f"{document.source_id}\x1f{document.canonical_url}\x1f{document.sha256}")
    if (
        document.id != expected_id
        or not _HEX.fullmatch(document.candidate_id)
        or not isinstance(document.owner_id, UUID)
        or (document.team_id is not None and not isinstance(document.team_id, UUID))
        or not _valid_text(document.source_id, 100)
        or not _valid_text(document.issuer, 200)
        or not _HEX.fullmatch(document.sha256)
        or (
            document.previous_sha256 is not None
            and (
                not _HEX.fullmatch(document.previous_sha256)
                or document.previous_sha256 == document.sha256
            )
        )
        or document.media_type not in MEDIA_EXTENSIONS
        or document.filename
        != f"original-{document.sha256[:12]}{MEDIA_EXTENSIONS[document.media_type]}"
        or type(document.byte_count) is not int
        or not 1 <= document.byte_count <= MAX_ORIGINAL_BYTES
        or not _valid_text(document.permitted_use, 1_000)
        or not _valid_text(document.acquisition_policy_id, 100)
        or type(document.omitted_passages) is not int
        or not 0 <= document.omitted_passages <= 200
        or document.original_language != "und"
        or document.publication_basis != "discovery_metadata_not_verified_in_document"
        or document.update_basis != "http_last_modified_not_publication_time"
        or not 1 <= len(document.requirement_ids) <= 12
        or len(set(document.requirement_ids)) != len(document.requirement_ids)
        or not 1 <= len(document.passages) <= MAX_PASSAGES
        or len(document.extraction_limitations) > 20
        or any(not _valid_text(note, 500) for note in document.extraction_limitations)
    ):
        raise ValueError("Malformed frozen original metadata")
    try:
        public_origin(document.requested_url)
        public_origin(document.canonical_url)
        for requirement_id in document.requirement_ids:
            stable_id(requirement_id, "original.requirement_id")
    except ValueError:
        raise ValueError("Malformed frozen original source or requirement") from None
    dates = (document.retrieved_at, document.published_at, document.http_last_modified_at)
    if (
        any(value is not None and value.utcoffset() is None for value in dates)
        or document.expires_at.utcoffset() is None
        or not document.retrieved_at < document.expires_at
        or document.expires_at > document.retrieved_at + timedelta(days=MAX_RETENTION_DAYS)
        or (
            document.etag is not None
            and (
                type(document.etag) is not str
                or len(document.etag) > 200
                or any(ord(character) < 32 for character in document.etag)
            )
        )
    ):
        raise ValueError("Malformed frozen original retention or HTTP metadata")
    seen_ids: set[str] = set()
    seen_units: set[int] = set()
    used_bytes = 0
    for passage in document.passages:
        if (
            type(passage.unit_index) is not int
            or passage.unit_index < 0
            or type(passage.start) is not int
            or type(passage.end) is not int
            or not _valid_text(passage.source_reference, 500)
            or type(passage.text) is not str
            or not 1 <= len(passage.text) <= MAX_PASSAGE_CHARACTERS
            or not passage.text.strip()
            or any(ord(char) < 32 and char not in "\n\r\t" for char in passage.text)
            or passage.content_kind != "original_passage"
            or passage.offset_basis != "extracted_unit_unicode_codepoints"
            or (passage.page is not None and (type(passage.page) is not int or passage.page < 1))
        ):
            raise ValueError("Malformed frozen original passage")
        text_hash = _digest(passage.text)
        expected_id = _digest(
            f"{document.id}\x1f{passage.unit_index}\x1f{passage.source_reference}"
            f"\x1f0\x1f{len(passage.text)}\x1f{text_hash}"
        )
        page_match = re.match(r"^PDF page ([1-9][0-9]*)(?:,|$)", passage.source_reference)
        expected_page = int(page_match[1]) if page_match else None
        if (
            passage.id != expected_id
            or passage.document_version_id != document.id
            or passage.original_sha256 != document.sha256
            or passage.text_sha256 != text_hash
            or passage.start != 0
            or passage.end != len(passage.text)
            or passage.page != expected_page
            or passage.id in seen_ids
            or passage.unit_index in seen_units
        ):
            raise ValueError("Frozen original passage integrity failed")
        seen_ids.add(passage.id)
        seen_units.add(passage.unit_index)
        used_bytes += len(passage.text.encode("utf-8"))
    if used_bytes > MAX_EXCERPT_BYTES:
        raise ValueError("Frozen original excerpts exceed the byte allowance")


def freeze_selected_original(
    document: OriginalDocumentVersion, passage_ids: tuple[str, ...]
) -> dict[str, Any]:
    """Select exact acquired passages and return only bounded JSON-safe metadata."""
    _validate(document)
    if (
        type(passage_ids) is not tuple
        or not 1 <= len(passage_ids) <= MAX_PASSAGES
        or len(set(passage_ids)) != len(passage_ids)
    ):
        raise ValueError("Select unique acquired original passages")
    wanted = set(passage_ids)
    selected = tuple(passage for passage in document.passages if passage.id in wanted)
    if len(selected) != len(wanted):
        raise ValueError("Selected passage is absent from the acquired original")
    frozen = replace(
        document,
        passages=selected,
        omitted_passages=document.omitted_passages + len(document.passages) - len(selected),
    )
    _validate(frozen)
    result = asdict(frozen)
    for key in _DATES:
        value = result[key]
        result[key] = value.isoformat() if value is not None else None
    result["owner_id"] = str(frozen.owner_id)
    result["team_id"] = str(frozen.team_id) if frozen.team_id is not None else None
    result["requirement_ids"] = list(frozen.requirement_ids)
    result["extraction_limitations"] = list(frozen.extraction_limitations)
    result["passages"] = [asdict(passage) for passage in frozen.passages]
    return {"schema_version": FROZEN_ORIGINAL_VERSION, "document": result}


def frozen_original_from_dict(data: object) -> OriginalDocumentVersion:
    """Decode a frozen selection without granting current access or retention rights."""
    if type(data) is not dict or set(data) != {"schema_version", "document"}:
        raise ValueError("Invalid frozen original snapshot")
    if type(data["schema_version"]) is not int or data["schema_version"] != FROZEN_ORIGINAL_VERSION:
        raise ValueError("Unsupported frozen original snapshot version")
    value = data["document"]
    if type(value) is not dict or set(value) != _DOCUMENT_KEYS:
        raise ValueError("Invalid frozen original fields")
    if (
        type(value["passages"]) is not list
        or len(value["passages"]) > MAX_PASSAGES
        or any(type(row) is not dict or set(row) != _PASSAGE_KEYS for row in value["passages"])
        or type(value["requirement_ids"]) is not list
        or type(value["extraction_limitations"]) is not list
    ):
        raise ValueError("Invalid frozen original passage fields")
    try:
        copied = dict(value)
        for key in _DATES:
            copied[key] = _date(
                copied[key], optional=key in ("published_at", "http_last_modified_at")
            )
        copied["owner_id"] = UUID(copied["owner_id"])
        copied["team_id"] = UUID(copied["team_id"]) if copied["team_id"] is not None else None
        copied["requirement_ids"] = tuple(copied["requirement_ids"])
        copied["extraction_limitations"] = tuple(copied["extraction_limitations"])
        copied["passages"] = tuple(OriginalPassage(**row) for row in copied["passages"])
        document = OriginalDocumentVersion(**copied)
        _validate(document)
    except (TypeError, ValueError, AttributeError, OverflowError):
        raise ValueError("Invalid frozen original integrity or provenance") from None
    return document
