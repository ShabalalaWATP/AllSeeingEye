"""Synthetic media only, never operator photographs or recordings."""

import io

from PIL import Image, ImageDraw, ImageFont


def synthetic_image(*, metadata: bool = False) -> bytes:
    image = Image.new("RGB", (1100, 220), "white")
    ImageDraw.Draw(image).text(
        (35, 60), "SYNTHETIC RAIL TEST 2026", fill="black", font=ImageFont.load_default(size=54)
    )
    exif = Image.Exif()
    if metadata:
        exif[271] = "Synthetic camera"
        exif[305] = "Synthetic editor"
        exif[306] = "2026:01:01 12:00:00"
        exif[37510] = b"Private EXIF bytes must not survive into previews"
    output = io.BytesIO()
    image.save(output, format="PNG", exif=exif)
    return output.getvalue()
