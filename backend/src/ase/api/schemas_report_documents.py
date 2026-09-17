"""Typed report publication and comparison responses for the frontend contract."""

import base64

from pydantic import BaseModel, ConfigDict

from ase.domain.report_documents import (
    BlockKind,
    ChangeKind,
    DocumentBlock,
    DocumentDiagram,
    DocumentFigure,
    DocumentListItem,
    DocumentTable,
    DocumentTableCell,
    ReportDocument,
)


class DocumentInlineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    text: str
    direction: str
    citation_numbers: list[int]


class DocumentListItemOut(BaseModel):
    text: str
    inlines: list[DocumentInlineOut]

    @classmethod
    def from_item(cls, item: DocumentListItem) -> "DocumentListItemOut":
        return cls(
            text=item.text,
            inlines=[DocumentInlineOut.model_validate(run) for run in item.inlines],
        )


class DocumentTableCellOut(BaseModel):
    text: str
    inlines: list[DocumentInlineOut]

    @classmethod
    def from_cell(cls, cell: DocumentTableCell) -> "DocumentTableCellOut":
        return cls(
            text=cell.text,
            inlines=[DocumentInlineOut.model_validate(run) for run in cell.inlines],
        )


class DocumentTableOut(BaseModel):
    title: str
    columns: list[str]
    rows: list[list[DocumentTableCellOut]]
    caption: str

    @classmethod
    def from_table(cls, table: DocumentTable) -> "DocumentTableOut":
        return cls(
            title=table.title,
            columns=list(table.columns),
            rows=[[DocumentTableCellOut.from_cell(cell) for cell in row] for row in table.rows],
            caption=table.caption,
        )


class DocumentFigureOut(BaseModel):
    title: str
    caption: str
    alt_text: str
    content_base64: str
    media_type: str
    width_px: int
    height_px: int
    citation_numbers: list[int]

    @classmethod
    def from_figure(cls, figure: DocumentFigure) -> "DocumentFigureOut":
        return cls(
            title=figure.title,
            caption=figure.caption,
            alt_text=figure.alt_text,
            content_base64=base64.b64encode(figure.content).decode("ascii"),
            media_type=figure.media_type,
            width_px=figure.width_px,
            height_px=figure.height_px,
            citation_numbers=list(figure.citation_numbers),
        )


class DocumentDiagramOut(BaseModel):
    """The drawing this application generated, carried as an image the page can show.

    The markup is base64 encoded exactly as a figure's bytes are, so a reader renders it
    as an image and never as markup inside the page.
    """

    title: str
    caption: str
    alt_text: str
    content_base64: str
    media_type: str
    citation_numbers: list[int]

    @classmethod
    def from_diagram(cls, diagram: DocumentDiagram) -> "DocumentDiagramOut":
        return cls(
            title=diagram.title,
            caption=diagram.caption,
            alt_text=diagram.alt_text,
            content_base64=base64.b64encode(diagram.svg.encode("utf-8")).decode("ascii"),
            media_type="image/svg+xml",
            citation_numbers=list(diagram.citation_numbers),
        )


class DocumentBlockOut(BaseModel):
    kind: BlockKind
    text: str
    inlines: list[DocumentInlineOut]
    items: list[DocumentListItemOut]
    ordered: bool
    table: DocumentTableOut | None
    figure: DocumentFigureOut | None
    diagram: DocumentDiagramOut | None

    @classmethod
    def from_block(cls, block: DocumentBlock) -> "DocumentBlockOut":
        return cls(
            kind=block.kind,
            text=block.text,
            inlines=[DocumentInlineOut.model_validate(run) for run in block.inlines],
            items=[DocumentListItemOut.from_item(item) for item in block.items],
            ordered=block.ordered,
            table=DocumentTableOut.from_table(block.table) if block.table else None,
            figure=DocumentFigureOut.from_figure(block.figure) if block.figure else None,
            diagram=DocumentDiagramOut.from_diagram(block.diagram) if block.diagram else None,
        )


class DocumentReferenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    number: int
    evidence_label: str
    title: str
    publisher: str
    published_at: str | None
    accessed_at: str
    url: str | None
    archive_url: str | None
    original_title: str | None
    language: str | None


class ReportPublicationOut(BaseModel):
    schema_version: int
    title: str
    reference: str
    language: str
    blocks: list[DocumentBlockOut]
    references: list[DocumentReferenceOut]

    @classmethod
    def from_document(cls, document: ReportDocument) -> "ReportPublicationOut":
        return cls(
            schema_version=document.schema_version,
            title=document.title,
            reference=document.reference,
            language=document.language,
            blocks=[DocumentBlockOut.from_block(block) for block in document.blocks],
            references=[
                DocumentReferenceOut.model_validate(reference) for reference in document.references
            ],
        )


class ReportChangeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    section: str
    path: str
    kind: ChangeKind
    before: str | None
    after: str | None


class ReportComparisonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    from_version: int
    to_version: int
    changes: list[ReportChangeOut]
