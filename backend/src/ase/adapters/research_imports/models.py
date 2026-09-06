"""Picklable, bounded output from an isolated untrusted-document parser.

The caller must run extraction in a killable subprocess with a deadline and OS
memory limits. Byte/structure checks reduce risk, but are not a parser sandbox.
Only extracted text and provenance leave the worker; original bytes are transient.
"""

from __future__ import annotations

from dataclasses import dataclass

MAX_UPLOAD_BYTES = 8 * 1024 * 1024
MAX_UNITS = 200
MAX_TEXT_CHARS = 200_000
MAX_UNIT_CHARS = 1_800
MAX_ROWS = 200
MAX_DEPTH = 32
MAX_NODES = 20_000
MAX_PAGES = 50
MAX_ZIP_ENTRIES = 256
MAX_ZIP_BYTES = 16 * 1024 * 1024
MAX_XML_BYTES = 4 * 1024 * 1024


class ImportRejected(ValueError):
    """Safe operator-facing reason; never contains parser excerpts or paths."""


@dataclass(frozen=True, slots=True)
class ExtractedUnit:
    reference: str
    text: str


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    filename: str
    media_type: str
    sha256: str
    units: tuple[ExtractedUnit, ...]
    limitations: tuple[str, ...]


class TextBudget:
    """Preserve locator boundaries; fail explicitly instead of silently dropping text."""

    def __init__(self) -> None:
        self.units: list[ExtractedUnit] = []
        self.characters = 0

    def add(self, reference: str, text: str) -> None:
        if not text.strip():
            return
        if self.characters + len(text) > MAX_TEXT_CHARS:
            raise ImportRejected("Extracted text exceeds the character limit.")
        chunks = (len(text) + MAX_UNIT_CHARS - 1) // MAX_UNIT_CHARS
        if len(self.units) + chunks > MAX_UNITS:
            raise ImportRejected("Document exceeds the extracted passage limit.")
        self.characters += len(text)
        for start in range(0, len(text), MAX_UNIT_CHARS):
            chunk = text[start : start + MAX_UNIT_CHARS]
            locator = reference
            if chunks > 1:
                locator += f", characters {start + 1}-{start + len(chunk)}"
            self.units.append(ExtractedUnit(locator, chunk))
