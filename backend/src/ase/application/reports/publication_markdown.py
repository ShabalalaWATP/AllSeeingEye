"""Safe Markdown projection of the canonical frozen report product."""

from __future__ import annotations

from ase.application.reports.export_text import plain_markdown
from ase.domain.report_documents import (
    BlockKind,
    DocumentBlock,
    DocumentInline,
    DocumentReference,
    ReportDocument,
)


def _inline(runs: tuple[DocumentInline, ...], fallback: str) -> str:
    if not runs:
        return plain_markdown(fallback)
    output: list[str] = []
    for run in runs:
        if run.citation_numbers:
            output.append(
                ", ".join(f"[{number}](#reference-{number})" for number in run.citation_numbers)
            )
        else:
            output.append(plain_markdown(run.text))
    return "".join(output)


def _reference(reference: DocumentReference) -> list[str]:
    date = plain_markdown(reference.published_at or "date not reported")
    publisher = plain_markdown(reference.publisher)
    title = plain_markdown(reference.title)
    lines = [f"### Reference {reference.number}", "", f"{publisher}. {title}. {date}."]
    if reference.original_title:
        lines.extend(("", f"Original title: {plain_markdown(reference.original_title)}."))
    if reference.url:
        lines.extend(("", f"[Open source]({reference.url})"))
    if reference.archive_url:
        lines.extend(("", f"[Archived copy]({reference.archive_url})"))
    lines.extend(("", f"Accessed {plain_markdown(reference.accessed_at)}.", ""))
    return lines


def _table_lines(block: DocumentBlock) -> list[str]:
    table = block.table
    if table is None:
        return []
    lines = [f"### {plain_markdown(table.title)}", ""]
    lines.append("| " + " | ".join(plain_markdown(value) for value in table.columns) + " |")
    lines.append("| " + " | ".join("---" for _ in table.columns) + " |")
    for row in table.rows:
        cells = " | ".join(_inline(cell.inlines, cell.text) for cell in row)
        lines.append(f"| {cells} |")
    if table.caption:
        lines.extend(("", f"*{plain_markdown(table.caption)}*"))
    return [*lines, ""]


def _figure_lines(block: DocumentBlock) -> list[str]:
    figure = block.figure
    if figure is None:
        return []
    citation = ""
    if figure.citation_numbers:
        citation = " " + ", ".join(
            f"[{number}](#reference-{number})" for number in figure.citation_numbers
        )
    return [
        f"### {plain_markdown(figure.title)}",
        "",
        plain_markdown(figure.alt_text),
        "",
        f"*{plain_markdown(figure.caption)}*{citation}",
        "",
    ]


def _block_lines(block: DocumentBlock) -> list[str]:
    kind = block.kind
    text = block.text
    if kind is BlockKind.TITLE:
        lines = [f"# {plain_markdown(text)}", ""]
    elif kind in {BlockKind.HEADING, BlockKind.ANNEX}:
        lines = [f"## {plain_markdown(text)}", ""]
    elif kind is BlockKind.SUBHEADING:
        lines = [f"### {plain_markdown(text)}", ""]
    elif kind is BlockKind.LIST:
        rows = []
        for number, item in enumerate(block.items, start=1):
            marker = f"{number}." if block.ordered else "-"
            rows.append(f"{marker} {_inline(item.inlines, item.text)}")
        lines = [*rows, ""]
    elif kind is BlockKind.TABLE:
        lines = _table_lines(block)
    elif kind is BlockKind.FIGURE:
        lines = _figure_lines(block)
    else:
        lines = [_inline(block.inlines, text), ""]
    return lines


def render_document_markdown(document: ReportDocument) -> str:
    """Render the ordered publication without interpreting any source or model markup."""
    lines: list[str] = []
    reference_index = 0
    for block in document.blocks:
        if block.kind is BlockKind.REFERENCE:
            if reference_index < len(document.references):
                lines.extend(_reference(document.references[reference_index]))
                reference_index += 1
            continue
        lines.extend(_block_lines(block))
    return "\n".join(lines).rstrip() + "\n"
