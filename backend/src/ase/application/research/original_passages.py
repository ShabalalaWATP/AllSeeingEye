"""Hash-bound source versions and exact extracted-unit passages, separate from translations.

Offsets refer to Unicode code points in the isolated parser's returned unit, not byte offsets
in a PDF/DOCX container. Source locators preserve page/chunk references without inventing them.
These values are transient until an authorised frozen-evidence integration admits them.
"""

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal
from uuid import UUID

from ase.application.access import AccessContext
from ase.application.ports.research_inputs import InputExtraction
from ase.application.research.original_candidates import (
    AdmittedOriginalCandidate,
    OriginalCandidateCatalogue,
)
from ase.application.research.original_policy import OriginalFetchResponse, OriginalSourcePolicy
from ase.domain.errors import InvalidRequest, NotFound

MAX_PASSAGES = 40
MAX_PASSAGE_CHARACTERS = 1800
MAX_EXCERPT_BYTES = 64 * 1024


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class OriginalPassage:
    id: str
    document_version_id: str
    original_sha256: str
    source_reference: str
    unit_index: int
    start: int
    end: int
    text: str = field(repr=False)
    text_sha256: str
    page: int | None
    offset_basis: Literal["extracted_unit_unicode_codepoints"] = "extracted_unit_unicode_codepoints"
    content_kind: Literal["original_passage"] = "original_passage"


@dataclass(frozen=True, slots=True)
class TranslatedOriginalPassage:
    id: str
    original_passage_id: str
    original_text_sha256: str
    language: str
    method: str
    text: str = field(repr=False)
    text_sha256: str
    content_kind: Literal["translated_derivative"] = "translated_derivative"


@dataclass(frozen=True, slots=True)
class OriginalDocumentVersion:
    id: str
    candidate_id: str
    owner_id: UUID
    team_id: UUID | None
    source_id: str
    issuer: str
    requested_url: str = field(repr=False)
    canonical_url: str = field(repr=False)
    retrieved_at: datetime
    published_at: datetime | None
    http_last_modified_at: datetime | None
    etag: str | None
    sha256: str
    previous_sha256: str | None
    media_type: str
    byte_count: int
    filename: str
    permitted_use: str
    acquisition_policy_id: str
    expires_at: datetime
    requirement_ids: tuple[str, ...]
    passages: tuple[OriginalPassage, ...]
    omitted_passages: int
    extraction_limitations: tuple[str, ...]
    original_language: Literal["und"] = "und"
    publication_basis: Literal["discovery_metadata_not_verified_in_document"] = (
        "discovery_metadata_not_verified_in_document"
    )
    update_basis: Literal["http_last_modified_not_publication_time"] = (
        "http_last_modified_not_publication_time"
    )


def _passage(
    version_id: str, digest: str, index: int, reference: str, text: str
) -> OriginalPassage:
    text_hash = _digest(text)
    key = _digest(f"{version_id}\x1f{index}\x1f{reference}\x1f0\x1f{len(text)}\x1f{text_hash}")
    page_match = re.match(r"^PDF page ([1-9][0-9]*)(?:,|$)", reference)
    return OriginalPassage(
        key,
        version_id,
        digest,
        reference,
        index,
        0,
        len(text),
        text,
        text_hash,
        int(page_match[1]) if page_match else None,
    )


def extracted_version(
    candidate: AdmittedOriginalCandidate,
    response: OriginalFetchResponse,
    extraction: InputExtraction,
    policy: OriginalSourcePolicy,
    retrieved_at: datetime,
    *,
    previous: OriginalDocumentVersion | None = None,
) -> OriginalDocumentVersion:
    digest = hashlib.sha256(response.body).hexdigest()
    if (
        extraction.sha256 != digest
        or extraction.media_type != response.media_type
        or not 1 <= len(extraction.events) <= 200
        or extraction.frames
        or extraction.parent_input_id is not None
        or extraction.parent_input_ids
    ):
        raise ValueError("Parser provenance does not match the acquired original")
    if previous is not None and (
        previous.owner_id != candidate.owner_id
        or previous.team_id != candidate.team_id
        or previous.source_id != candidate.source_id
        or previous.canonical_url != response.canonical_url
    ):
        raise ValueError("A correction must belong to the same source and canonical URL")
    version_id = _digest(f"{candidate.source_id}\x1f{response.canonical_url}\x1f{digest}")
    passages: list[OriginalPassage] = []
    used_bytes = 0
    for index, event in enumerate(extraction.events):
        reference = event.attributes.get("source_reference")
        text = event.summary
        if (
            event.subtype != "document_passage"
            or event.transformations
            or event.attributes.get("original_sha256") != digest
            or not isinstance(reference, str)
            or not 1 <= len(reference) <= 500
            or not isinstance(text, str)
            or not 1 <= len(text) <= MAX_PASSAGE_CHARACTERS
            or not text.strip()
            or any(ord(char) < 32 and char not in "\n\r\t" for char in text)
        ):
            raise ValueError("Parser passage provenance is invalid")
        size = len(text.encode("utf-8"))
        if len(passages) < MAX_PASSAGES and used_bytes + size <= MAX_EXCERPT_BYTES:
            passages.append(_passage(version_id, digest, index, reference, text))
            used_bytes += size
    if not passages:
        raise ValueError("No bounded original passage is available")
    previous_hash = previous.sha256 if previous is not None and previous.sha256 != digest else None
    return OriginalDocumentVersion(
        version_id,
        candidate.id,
        candidate.owner_id,
        candidate.team_id,
        candidate.source_id,
        candidate.issuer,
        candidate.requested_url,
        response.canonical_url,
        retrieved_at,
        candidate.published_at,
        response.last_modified_at,
        response.etag,
        digest,
        previous_hash,
        response.media_type,
        len(response.body),
        extraction.filename,
        policy.permitted_use,
        policy.policy_id,
        retrieved_at + timedelta(days=policy.retention_days),
        candidate.requirement_ids,
        tuple(passages),
        len(extraction.events) - len(passages),
        extraction.limitations,
    )


def require_original_passage(
    document: OriginalDocumentVersion,
    passage_id: str,
    *,
    catalogue: OriginalCandidateCatalogue,
    access: AccessContext,
    now: datetime,
    source_enabled: bool,
    revoked: bool,
) -> OriginalPassage:
    """Caller must supply current access/source/retention state, never a cached permission."""
    candidate = catalogue.get(document.candidate_id, access)
    access.require_same_scope(
        catalogue.owner_id, catalogue.team_id, document.owner_id, document.team_id
    )
    if (
        not source_enabled
        or revoked
        or now >= document.expires_at
        or document.source_id != candidate.source_id
    ):
        raise NotFound("Original passage is unavailable")
    matches = [passage for passage in document.passages if passage.id == passage_id]
    if len(matches) != 1:
        raise NotFound("Original passage not found")
    passage = matches[0]
    expected = _passage(
        document.id, document.sha256, passage.unit_index, passage.source_reference, passage.text
    )
    if passage != expected:
        raise InvalidRequest("Original passage failed its citation integrity check")
    return passage


def translated_derivative(
    original: OriginalPassage, text: str, *, language: str, method: str
) -> TranslatedOriginalPassage:
    """Record an externally produced translation; it never becomes an original passage."""
    if (
        original
        != _passage(
            original.document_version_id,
            original.original_sha256,
            original.unit_index,
            original.source_reference,
            original.text,
        )
        or not re.fullmatch(r"[a-z]{2,3}(?:-[a-z0-9]{2,8})?", language)
        or not 1 <= len(text) <= MAX_PASSAGE_CHARACTERS
        or not text.strip()
        or not 1 <= len(method) <= 100
        or any(ord(char) < 32 and char not in "\n\r\t" for char in text)
        or any(ord(char) < 32 for char in method)
    ):
        raise ValueError("Invalid translated passage metadata")
    digest = _digest(text)
    return TranslatedOriginalPassage(
        _digest(f"{original.id}\x1f{language}\x1f{method}\x1f{digest}"),
        original.id,
        original.text_sha256,
        language,
        method,
        text,
        digest,
    )
