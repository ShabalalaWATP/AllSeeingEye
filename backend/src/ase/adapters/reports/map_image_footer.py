"""Bounded image credit footer with packaged glyphs and explicit unsupported characters."""

import io

from PIL import Image, ImageDraw, ImageFont

from ase.adapters.reports.font_support import FONT_DIRECTORY, cjk_font, font_characters
from ase.domain.errors import InvalidRequest


def image_footer(image: Image.Image, lines: list[str]) -> bytes:
    latin = ImageFont.truetype(str(FONT_DIRECTORY / "DejaVuLGCSans.ttf"), 12)
    cjk_name, chinese_chars = cjk_font("zh-Hans")
    chinese = ImageFont.truetype(str(FONT_DIRECTORY / f"{cjk_name}-Regular.ttf"), 12)
    latin_chars = font_characters()
    rows: list[list[tuple[str, ImageFont.FreeTypeFont, float]]] = []
    for line in lines:
        row: list[tuple[str, ImageFont.FreeTypeFont, float]] = []
        width = 0.0
        for char in line:
            code = ord(char)
            font = latin if code in latin_chars else chinese
            text = char if code in latin_chars or code in chinese_chars else f"[U+{code:04X}]"
            if text != char:
                font = latin
            size = font.getlength(text)
            if width + size > image.width - 24:
                rows.append(row)
                row, width = [], 0.0
            row.append((text, font, width))
            width += size
        rows.append(row)
    height = image.height + 20 + 17 * len(rows)
    if height > 2048 or height * image.width > 4_000_000:
        raise InvalidRequest(
            "The image plus attribution footer exceeds 2048 pixels or 4 MP. "
            "Use a smaller capture or fewer visible annotations."
        )
    canvas = Image.new("RGB", (image.width, height), "#080b12")
    canvas.paste(image)
    draw = ImageDraw.Draw(canvas)
    for index, row in enumerate(rows):
        for text, font, x in row:
            draw.text((12 + x, image.height + 10 + 17 * index), text, font=font, fill="#e4e9f0")
    output = io.BytesIO()
    canvas.save(output, format="PNG")
    return output.getvalue()
