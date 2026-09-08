"""Escaped semantic HTML projection, with no executable or external resources.

This adapter does not run a browser or declare PDF language/accessibility support.
"""

from html import escape

from ase.domain.errors import InvalidRequest
from ase.domain.languages import valid_language_code
from ase.domain.report_documents import BlockKind, ReportDocument

MAX_HTML_BYTES = 4 * 1024 * 1024
MAX_CHARACTERS = 300_000
MAX_BLOCKS = 2_000
MAX_BLOCK_CHARACTERS = 16_000
_TAGS = {
    BlockKind.TITLE: "h1",
    BlockKind.HEADING: "h2",
    BlockKind.ANNEX: "h2",
    BlockKind.SUBHEADING: "h3",
    BlockKind.TEXT: "p",
    BlockKind.WARNING: "p",
    BlockKind.METADATA: "p",
}
_CSS = """
@page { size: A4; margin: 16mm; }
body { font-family: sans-serif; font-size: 11pt; line-height: 1.6; color: #111; }
main { overflow-wrap: anywhere; }
p,h1,h2,h3 { white-space: pre-wrap; }
h1,h2,h3 { break-after: avoid; }
p { orphans: 2; widows: 2; }
.annex { break-before: page; }
.metadata { font-size: 9pt; color: #444; }
.warning { border-inline-start: 3px solid #853200; padding-inline-start: 8px; }
"""


def render_html(document: ReportDocument) -> bytes:
    """Render bounded immutable blocks; original text never becomes HTML syntax."""
    if (
        len(document.blocks) > MAX_BLOCKS
        or len(document.title) > MAX_BLOCK_CHARACTERS
        or len(document.reference) > MAX_BLOCK_CHARACTERS
        or sum(len(block.text) for block in document.blocks) > MAX_CHARACTERS
        or any(len(block.text) > MAX_BLOCK_CHARACTERS for block in document.blocks)
    ):
        raise InvalidRequest("This report exceeds the HTML document size limit.")
    language = document.language if valid_language_code(document.language) else "und"
    direction = "rtl" if language.lower().split("-")[0] in {"ar", "fa"} else "ltr"
    parts = [
        f'<!doctype html><html lang="{escape(language, quote=True)}" dir="{direction}">',
        '<head><meta charset="utf-8">',
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
        "style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'\">",
        f"<title>{escape(document.title)}</title><style>{_CSS}</style></head><body><main>",
    ]
    for block in document.blocks:
        tag = _TAGS[block.kind]
        content = (
            "".join(f'<bdi dir="{run.direction}">{escape(run.text)}</bdi>' for run in block.inlines)
            if block.inlines
            else escape(block.text)
        )
        parts.append(f'<{tag} class="{block.kind.value}" dir="auto">{content}</{tag}>')
    parts.append("</main></body></html>")
    result = "".join(parts).encode("utf-8")
    if len(result) > MAX_HTML_BYTES:
        raise InvalidRequest("This report exceeds the HTML document byte limit.")
    return result
