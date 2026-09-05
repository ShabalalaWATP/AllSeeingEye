"""Plain-text document blocks shared by report exports and their renderers."""

from dataclasses import dataclass
from enum import StrEnum


class ExportFormat(StrEnum):
    PDF = "pdf"
    DOCX = "docx"


class BlockKind(StrEnum):
    TITLE = "title"
    HEADING = "heading"
    ANNEX = "annex"
    SUBHEADING = "subheading"
    TEXT = "text"
    WARNING = "warning"
    METADATA = "metadata"


@dataclass(frozen=True, slots=True)
class DocumentBlock:
    kind: BlockKind
    text: str


@dataclass(frozen=True, slots=True)
class ReportDocument:
    title: str
    reference: str
    blocks: tuple[DocumentBlock, ...]


@dataclass(frozen=True, slots=True)
class ReportFile:
    content: bytes
    media_type: str
    filename: str


class ChangeKind(StrEnum):
    ADDED = "added"
    REMOVED = "removed"
    CHANGED = "changed"


@dataclass(frozen=True, slots=True)
class ReportChange:
    section: str
    path: str
    kind: ChangeKind
    before: str | None
    after: str | None


@dataclass(frozen=True, slots=True)
class ReportComparison:
    from_version: int
    to_version: int
    changes: tuple[ReportChange, ...]
