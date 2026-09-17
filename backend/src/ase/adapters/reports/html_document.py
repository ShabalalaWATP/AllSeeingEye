"""Escaped semantic HTML projection with fixed, local-only structured content."""

import base64
import re
from html import escape
from urllib.parse import urlsplit

from ase.adapters.reports.diagram_validation import verify_document_diagrams
from ase.adapters.reports.document_validation import validate_document_content
from ase.adapters.reports.figure_validation import verify_document_figures
from ase.domain.errors import InvalidRequest
from ase.domain.languages import valid_language_code
from ase.domain.report_documents import (
    BlockKind,
    DocumentInline,
    DocumentReference,
    ReportDocument,
)

MAX_HTML_BYTES = 4 * 1024 * 1024
_CITATION_NUMBER = re.compile(r"\d+")
_TAGS = {
    BlockKind.TITLE: "h1",
    BlockKind.HEADING: "h2",
    BlockKind.ANNEX: "h2",
    BlockKind.SUBHEADING: "h3",
    BlockKind.TEXT: "p",
    BlockKind.WARNING: "p",
    BlockKind.METADATA: "p",
    BlockKind.REFERENCE: "p",
}
_CSS = """
@page { size: A4; margin: 16mm; }
body { font-family: sans-serif; font-size: 11pt; line-height: 1.6; color: #111; }
main { overflow-wrap: anywhere; }
p,h1,h2,h3 { white-space: pre-wrap; }
h1,h2,h3,figcaption { break-after: avoid; }
p,li { orphans: 2; widows: 2; }
.annex { break-before: page; }
.metadata,.reference,figcaption { font-size: 9pt; color: #444; }
.warning { border-inline-start: 3px solid #853200; padding-inline-start: 8px; }
table { width: 100%; border-collapse: collapse; margin-block: 6mm; font-size: 9pt; }
thead { display: table-header-group; }
th { background: #183746; color: white; }
th,td { border: 1px solid #bac2c9; padding: 1.5mm; text-align: start; vertical-align: top; }
figure { margin: 6mm 0; break-inside: avoid; text-align: center; }
figure img { display: block; max-width: 100%; max-height: 170mm; margin: auto; }
figure svg { display: block; max-width: 100%; height: auto; margin: auto; }
"""


def _safe_url(value: str | None) -> str | None:
    if not value or len(value) > 2_048 or any(ord(char) < 32 for char in value):
        return None
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    if parsed.username is not None or parsed.password is not None:
        return None
    return value


def _inline_html(inline: DocumentInline) -> str:
    if not inline.citation_numbers:
        return f'<bdi dir="{inline.direction}">{escape(inline.text)}</bdi>'
    matches = tuple(_CITATION_NUMBER.finditer(inline.text))
    if tuple(int(match.group()) for match in matches) != inline.citation_numbers:
        return f'<bdi dir="{inline.direction}">{escape(inline.text)}</bdi>'
    numbers = iter(inline.citation_numbers)
    output: list[str] = []
    cursor = 0
    for match in matches:
        try:
            number = next(numbers)
        except StopIteration:
            break
        output.append(escape(inline.text[cursor : match.start()]))
        output.append(f'<a href="#reference-{number}">{match.group()}</a>')
        cursor = match.end()
    output.append(escape(inline.text[cursor:]))
    return f'<bdi dir="{inline.direction}">{"".join(output)}</bdi>'


def _text_html(text: str, inlines: tuple[DocumentInline, ...]) -> str:
    return "".join(_inline_html(run) for run in inlines) if inlines else escape(text)


def _reference_html(reference: DocumentReference, text: str) -> str:
    anchor = f'<span id="reference-{reference.number}"></span>'
    urls = list(
        dict.fromkeys(
            url
            for candidate in (reference.url, reference.archive_url)
            if (url := _safe_url(candidate)) is not None
        )
    )
    if not urls:
        return anchor + escape(text)
    parts = [anchor]
    cursor = 0
    while urls:
        matches = [(text.find(url, cursor), -len(url), url) for url in urls]
        matches = [match for match in matches if match[0] >= 0]
        if not matches:
            break
        start, _, url = min(matches)
        parts.append(escape(text[cursor:start]))
        parts.append(f'<a href="{escape(url, quote=True)}" rel="noreferrer">{escape(url)}</a>')
        cursor = start + len(url)
        urls.remove(url)
    parts.append(escape(text[cursor:]))
    return "".join(parts)


def render_html(document: ReportDocument) -> bytes:
    """Render bounded immutable content; original text never becomes HTML syntax."""
    validate_document_content(document)
    verify_document_diagrams(document)
    figures = verify_document_figures(document)
    language = document.language if valid_language_code(document.language) else "und"
    direction = "rtl" if language.lower().split("-")[0] in {"ar", "fa"} else "ltr"
    parts = [
        f'<!doctype html><html lang="{escape(language, quote=True)}" dir="{direction}">',
        '<head><meta charset="utf-8">',
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
        "style-src 'unsafe-inline'; img-src data:; base-uri 'none'; form-action 'none'\">",
        f"<title>{escape(document.title)}</title><style>{_CSS}</style></head><body><main>",
    ]
    reference_index = 0
    for block in document.blocks:
        if block.kind is BlockKind.LIST:
            tag = "ol" if block.ordered else "ul"
            items = "".join(
                f"<li>{_text_html(item.text, item.inlines)}</li>" for item in block.items
            )
            parts.append(f"<{tag}>{items}</{tag}>")
            continue
        if block.kind is BlockKind.TABLE and block.table:
            headers = "".join(f"<th>{escape(value)}</th>" for value in block.table.columns)
            rows = "".join(
                "<tr>"
                + "".join(f"<td>{_text_html(cell.text, cell.inlines)}</td>" for cell in row)
                + "</tr>"
                for row in block.table.rows
            )
            caption = (
                f"<caption>{escape(block.table.title)}. {escape(block.table.caption)}</caption>"
            )
            parts.append(
                f"<table>{caption}<thead><tr>{headers}</tr></thead><tbody>{rows}</tbody></table>"
            )
            continue
        if block.kind is BlockKind.FIGURE and block.figure:
            figure = block.figure
            encoded = base64.b64encode(figures[id(figure)].content).decode("ascii")
            citation = (
                f" [{', '.join(str(number) for number in figure.citation_numbers)}]"
                if figure.citation_numbers
                else ""
            )
            citation_html = (
                _inline_html(DocumentInline(citation, "ltr", figure.citation_numbers))
                if citation
                else ""
            )
            parts.append(
                f'<figure><img src="data:{figure.media_type};base64,{encoded}" '
                f'alt="{escape(figure.alt_text, quote=True)}">'
                f"<figcaption>{escape(figure.title)}. {escape(figure.caption)}"
                f"{citation_html}</figcaption></figure>"
            )
            continue
        if block.kind is BlockKind.DIAGRAM and block.diagram:
            diagram = block.diagram
            citation = (
                f" [{', '.join(str(number) for number in diagram.citation_numbers)}]"
                if diagram.citation_numbers
                else ""
            )
            citation_html = (
                _inline_html(DocumentInline(citation, "ltr", diagram.citation_numbers))
                if citation
                else ""
            )
            parts.append(
                f"<figure>{diagram.svg}<figcaption>{escape(diagram.title)}. "
                f"{escape(diagram.caption)}{citation_html}</figcaption></figure>"
            )
            continue
        tag = _TAGS[block.kind]
        if block.kind is BlockKind.REFERENCE and reference_index < len(document.references):
            content = _reference_html(document.references[reference_index], block.text)
            reference_index += 1
        else:
            content = _text_html(block.text, block.inlines)
        parts.append(f'<{tag} class="{block.kind.value}" dir="auto">{content}</{tag}>')
    parts.append("</main></body></html>")
    result = "".join(parts).encode("utf-8")
    if len(result) > MAX_HTML_BYTES:
        raise InvalidRequest("This report exceeds the HTML document byte limit.")
    return result
