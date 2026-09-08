"""Fixed print assets layered onto the escaped report projection."""

import base64
import hashlib
from pathlib import Path

from ase.adapters.reports.html_document import render_html
from ase.domain.errors import InvalidRequest
from ase.domain.report_documents import ReportDocument

FONTS = (
    ("Regular", 400, "7ed3fe069312aceac454f17cf613a30f95271d6ed7ce58005ed4d016bd3823d7"),
    ("Bold", 700, "5ccd1a8914f7c7e8aa8050f2c7c37b10fc5e855f06583c2a2248a436aad3fc0f"),
)
MAX_PRINT_HTML_BYTES = 8 * 1024 * 1024


def render_print_html(document: ReportDocument) -> bytes:
    styles = []
    for weight, code, digest in FONTS:
        data = (Path(__file__).with_name("fonts") / f"NotoSansArabic-{weight}.ttf").read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise InvalidRequest("The verified report font is unavailable.")
        encoded = base64.b64encode(data).decode("ascii")
        styles.append(
            f"@font-face{{font-family:ASENotoArabic;font-weight:{code};"
            f"src:url(data:font/ttf;base64,{encoded}) format('truetype');}}"
        )
    # Replace only adapter-owned scaffolding; untrusted document text is already escaped.
    html = render_html(document).decode("utf-8")
    html = html.replace(
        "style-src 'unsafe-inline';", "style-src 'unsafe-inline'; font-src data:;", 1
    )
    html = html.replace("<style>", "<style>" + "".join(styles), 1)
    html = html.replace("font-family: sans-serif;", "font-family: ASENotoArabic, sans-serif;", 1)
    result = html.encode("utf-8")
    if len(result) > MAX_PRINT_HTML_BYTES:
        raise InvalidRequest("The print document exceeds its byte limit.")
    return result
