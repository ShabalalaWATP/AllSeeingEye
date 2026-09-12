"""Bounded semantic report product shared by the reader and every export."""

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
    LIST = "list"
    TABLE = "table"
    FIGURE = "figure"
    REFERENCE = "reference"


@dataclass(frozen=True, slots=True)
class DocumentInline:
    """A semantic text run, never markup or an arbitrary live link."""

    text: str
    direction: Literal["auto", "ltr", "rtl"] = "auto"
    citation_numbers: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if (
            not isinstance(self.text, str)
            or self.direction not in {"auto", "ltr", "rtl"}
            or not isinstance(self.citation_numbers, tuple)
            or len(self.citation_numbers) > 32
            or any(type(number) is not int or number < 1 for number in self.citation_numbers)
            or len(set(self.citation_numbers)) != len(self.citation_numbers)
        ):
            raise ValueError("Invalid document inline text or direction")


@dataclass(frozen=True, slots=True)
class DocumentListItem:
    text: str
    inlines: tuple[DocumentInline, ...] = ()

    def __post_init__(self) -> None:
        _validate_text_projection(self.text, self.inlines)


@dataclass(frozen=True, slots=True)
class DocumentTableCell:
    text: str
    inlines: tuple[DocumentInline, ...] = ()

    def __post_init__(self) -> None:
        _validate_text_projection(self.text, self.inlines)


@dataclass(frozen=True, slots=True)
class DocumentTable:
    title: str
    columns: tuple[str, ...]
    rows: tuple[tuple[DocumentTableCell, ...], ...]
    caption: str = ""

    def __post_init__(self) -> None:
        if (
            not self.title
            or not 1 <= len(self.columns) <= 20
            or len(self.rows) > 500
            or any(len(row) != len(self.columns) for row in self.rows)
        ):
            raise ValueError("Invalid bounded document table")


@dataclass(frozen=True, slots=True)
class DocumentFigure:
    title: str
    caption: str
    alt_text: str
    content: bytes
    media_type: Literal["image/png", "image/jpeg"]
    width_px: int
    height_px: int
    citation_numbers: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if (
            not self.title
            or not self.alt_text
            or not self.content
            or len(self.content) > 10_000_000
            or self.media_type not in {"image/png", "image/jpeg"}
            or not 1 <= self.width_px <= 10_000
            or not 1 <= self.height_px <= 10_000
            or len(self.citation_numbers) > 32
            or any(type(number) is not int or number < 1 for number in self.citation_numbers)
            or len(set(self.citation_numbers)) != len(self.citation_numbers)
        ):
            raise ValueError("Invalid bounded document figure")


@dataclass(frozen=True, slots=True)
class DocumentReference:
    number: int
    evidence_label: str
    title: str
    publisher: str
    published_at: str | None
    accessed_at: str
    url: str | None = None
    archive_url: str | None = None
    original_title: str | None = None
    language: str | None = None

    def __post_init__(self) -> None:
        if self.number < 1 or not self.evidence_label or not self.title or not self.publisher:
            raise ValueError("Invalid document reference")


@dataclass(frozen=True, slots=True)
class DocumentBlock:
    kind: BlockKind
    text: str
    inlines: tuple[DocumentInline, ...] = ()
    items: tuple[DocumentListItem, ...] = ()
    ordered: bool = False
    table: DocumentTable | None = None
    figure: DocumentFigure | None = None

    def __post_init__(self) -> None:
        _validate_text_projection(self.text, self.inlines)
        if len(self.items) > 500 or any(
            not isinstance(item, DocumentListItem) for item in self.items
        ):
            raise ValueError("Provide at most 500 immutable list items")
        payloads = (
            int(bool(self.items)) + int(self.table is not None) + int(self.figure is not None)
        )
        if payloads > 1:
            raise ValueError("A document block may contain one structured payload")
        if self.kind is BlockKind.LIST and not self.items:
            raise ValueError("A list block requires items")
        if self.kind is BlockKind.TABLE and self.table is None:
            raise ValueError("A table block requires a table")
        if self.kind is BlockKind.FIGURE and self.figure is None:
            raise ValueError("A figure block requires a figure")


def _validate_text_projection(text: str, inlines: tuple[DocumentInline, ...]) -> None:
    if (
        not isinstance(text, str)
        or not isinstance(inlines, tuple)
        or len(inlines) > 256
        or any(not isinstance(run, DocumentInline) for run in inlines)
    ):
        raise ValueError("Provide at most 256 immutable document inlines")
    if inlines and "".join(run.text for run in inlines) != text:
        raise ValueError("Document inlines must preserve the plain-text projection")


@dataclass(frozen=True, slots=True)
class ReportDocument:
    title: str
    reference: str
    blocks: tuple[DocumentBlock, ...]
    language: str = "en"
    references: tuple[DocumentReference, ...] = ()
    schema_version: int = 1

    def __post_init__(self) -> None:
        if self.schema_version < 1 or len(self.references) > 500:
            raise ValueError("Invalid report document schema or reference count")
        numbers = tuple(reference.number for reference in self.references)
        if numbers != tuple(range(1, len(numbers) + 1)):
            raise ValueError("Document references must be consecutively numbered")
        known = set(numbers)
        cited = {
            number
            for block in self.blocks
            for run in (
                *block.inlines,
                *(run for item in block.items for run in item.inlines),
                *(
                    run
                    for row in (block.table.rows if block.table else ())
                    for cell in row
                    for run in cell.inlines
                ),
            )
            for number in run.citation_numbers
        }
        cited.update(
            number
            for block in self.blocks
            if block.figure is not None
            for number in block.figure.citation_numbers
        )
        if not cited <= known:
            raise ValueError("Document contains an orphan citation")


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
