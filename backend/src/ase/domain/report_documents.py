"""Plain-text document blocks shared by report exports and their renderers."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal
from uuid import UUID


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
class DocumentInline:
    """A semantic text run, never markup or a live link."""

    text: str
    direction: Literal["auto", "ltr", "rtl"] = "auto"

    def __post_init__(self) -> None:
        if not isinstance(self.text, str) or self.direction not in {"auto", "ltr", "rtl"}:
            raise ValueError("Invalid document inline text or direction")


@dataclass(frozen=True, slots=True)
class DocumentBlock:
    kind: BlockKind
    text: str
    inlines: tuple[DocumentInline, ...] = ()

    def __post_init__(self) -> None:
        if (
            not isinstance(self.inlines, tuple)
            or len(self.inlines) > 256
            or any(not isinstance(run, DocumentInline) for run in self.inlines)
        ):
            raise ValueError("Provide at most 256 immutable document inlines")
        if self.inlines and "".join(run.text for run in self.inlines) != self.text:
            raise ValueError("Document inlines must preserve the plain-text projection")


@dataclass(frozen=True, slots=True)
class ReportDocument:
    title: str
    reference: str
    blocks: tuple[DocumentBlock, ...]
    language: str = "en"


@dataclass(frozen=True, slots=True)
class ReportFile:
    content: bytes
    media_type: str
    filename: str
    report_version_id: UUID | None = None
    version_number: int | None = None


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
