"""Packaged Latin, Greek and Cyrillic fonts with identical body/heading glyph coverage."""

from functools import cache
from pathlib import Path
from threading import Lock
from typing import cast

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT_REGULAR = "ASEDejaVuLGC"
FONT_BOLD = "ASEDejaVuLGCBold"
FONT_DIRECTORY = Path(__file__).with_name("fonts")
_REGISTRATION = Lock()
# These controls have blank glyphs in the font. Expose them rather than carrying
# invisible direction overrides into an export which has no bidirectional layout.
_BIDI_CONTROLS = frozenset({0x061C, 0x200E, 0x200F, *range(0x202A, 0x202F), *range(0x2066, 0x206A)})


def font_characters() -> frozenset[int]:
    """Register both weights atomically because exports can run on two worker threads.

    The unmodified upstream LGC subset excludes scripts that need shaping or fonts
    this renderer does not provide. Missing characters keep the PDF's explicit
    code-point fallback; it must not claim Arabic, CJK or general Unicode support.
    """
    with _REGISTRATION:
        return _registered_characters()


@cache
def _registered_characters() -> frozenset[int]:
    coverages = []
    for alias, filename in (
        (FONT_REGULAR, "DejaVuLGCSans.ttf"),
        (FONT_BOLD, "DejaVuLGCSans-Bold.ttf"),
    ):
        if alias not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(alias, str(FONT_DIRECTORY / filename)))
        font = cast(TTFont, pdfmetrics.getFont(alias))
        coverages.append(frozenset(font.face.charToGlyph))
    return (coverages[0] & coverages[1]) - _BIDI_CONTROLS
