"""Bounded private imports; no fetches, persistence or publication to the live store.

``extract_upload`` is a synchronous, picklable subprocess entrypoint. The caller
must impose a process deadline and memory budget, and terminate the worker on
cancellation. Never wrap untrusted parsers in an unkillable thread timeout.
``events_from_extraction`` runs after the worker returns, in the parent process.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import PurePath

from ase.adapters.research_imports.documents import extract_docx, extract_pdf
from ase.adapters.research_imports.models import (
    MAX_UPLOAD_BYTES,
    ExtractionResult,
    ImportRejected,
    TextBudget,
)
from ase.adapters.research_imports.text import extract_csv, extract_json, extract_text
from ase.domain.events import (
    Category,
    Event,
    Reliability,
    content_hash,
    event_id,
    freeze_attributes,
)

__all__ = ["ExtractionResult", "ImportRejected", "events_from_extraction", "extract_upload"]

MEDIA_TYPES = {
    ".txt": "text/plain",
    ".csv": "text/csv",
    ".json": "application/json",
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def extract_upload(data: bytes, filename: str) -> ExtractionResult:
    """Extract a supported upload without opening a path or retaining its original bytes.

    Filename is a display label, never a filesystem destination. Unsupported types,
    malformed content and limit violations fail without returning partial evidence.
    """
    if not data or len(data) > MAX_UPLOAD_BYTES:
        raise ImportRejected("Upload is empty or exceeds the 8 MiB size limit.")
    if (
        not filename
        or len(filename) > 120
        or any(ord(char) < 32 for char in filename)
        or any(char in filename for char in "/\\:")
    ):
        raise ImportRejected("Use a plain filename of at most 120 characters.")
    extension = PurePath(filename).suffix.lower()
    parser = {
        ".txt": extract_text,
        ".csv": extract_csv,
        ".json": extract_json,
        ".pdf": extract_pdf,
        ".docx": extract_docx,
    }.get(extension)
    if parser is None:
        raise ImportRejected("Supported imports are UTF-8 TXT, CSV, JSON, PDF and DOCX.")
    budget = TextBudget()
    try:
        limitations = parser(data, budget)
    except ImportRejected:
        raise
    except Exception:
        # Third-party parser messages may include attacker text and internal paths.
        raise ImportRejected("The document is malformed or uses an unsupported feature.") from None
    if not budget.units:
        raise ImportRejected("No text could be extracted; scanned documents require OCR.")
    return ExtractionResult(
        filename=filename,
        media_type=MEDIA_TYPES[extension],
        sha256=hashlib.sha256(data).hexdigest(),
        units=tuple(budget.units),
        limitations=limitations,
    )


def events_from_extraction(
    result: ExtractionResult,
    captured_at: datetime,
    source_id: str = "research_import",
) -> tuple[Event, ...]:
    """Convert extracted passages to private F6 evidence, with honest timestamp semantics."""
    if captured_at.tzinfo is None or captured_at.utcoffset() is None:
        raise ImportRejected("Capture time must include a timezone.")
    return tuple(
        Event(
            id=event_id(source_id, f"{result.sha256}:{unit.reference}"),
            source_id=source_id,
            category=Category.NEWS,
            subtype="document_passage",
            title=f"{result.filename}: {unit.reference}"[:300],
            summary=unit.text,
            published_at=None,
            observed_at=captured_at,
            reliability=Reliability.F,
            language="und",
            grade_rationale="Uploaded material: reliability and factual accuracy unassessed.",
            attributes=freeze_attributes(
                {
                    "filename": result.filename,
                    "source_reference": unit.reference,
                    "original_sha256": result.sha256,
                    "media_type": result.media_type,
                    "timestamp_basis": "capture time; original publication time unknown",
                    "extraction_limitations": " ".join(result.limitations),
                }
            ),
            content_hash=content_hash(unit.text),
        )
        for unit in result.units
    )
