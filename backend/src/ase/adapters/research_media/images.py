"""Pillow metadata and sanitised pixel decoding, followed by optional local OCR."""

import hashlib
import io
import warnings
from pathlib import Path

from PIL import Image, ImageOps

from ase.adapters.research_imports.models import ImportRejected, TextBudget
from ase.adapters.research_media.models import (
    MAX_DIMENSION,
    MAX_FRAME_BYTES,
    MAX_PIXELS,
    MediaFrame,
)
from ase.adapters.research_media.tools import run_tool

EXIF_FIELDS = {
    271: "camera_make",
    272: "camera_model",
    305: "software",
    306: "metadata_datetime",
    36867: "metadata_datetime_original",
    36881: "metadata_timezone_original",
}


def decode_image(data: bytes) -> tuple[Image.Image, tuple[tuple[str, str], ...]]:
    previous = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data), formats=["PNG", "JPEG", "WEBP"]) as source:
                width, height = source.size
                if (
                    width * height > MAX_PIXELS
                    or max(width, height) > MAX_DIMENSION
                    or getattr(source, "is_animated", False)
                ):
                    raise ImportRejected("Image dimensions or animation exceed supported limits.")
                metadata = [
                    ("format", str(source.format)),
                    ("width", str(width)),
                    ("height", str(height)),
                ]
                exif = source.getexif()
                for tag, label in EXIF_FIELDS.items():
                    value = exif.get(tag)
                    if isinstance(value, (str, int, float)) and str(value).strip():
                        metadata.append((label, str(value)[:200]))
                pixels = ImageOps.exif_transpose(source).convert("RGB")
                # A new pixel-only image prevents EXIF, comments and profiles leaking into previews.
                clean = Image.frombytes("RGB", pixels.size, pixels.tobytes())
                return clean, tuple(metadata)
    except ImportRejected:
        raise
    except Exception:
        raise ImportRejected("The image is malformed or exceeds decoding limits.") from None
    finally:
        Image.MAX_IMAGE_PIXELS = previous


def preview(image: Image.Image, seconds: float = 0.0) -> MediaFrame:
    small = image.copy()
    small.thumbnail((512, 512))
    buffer = io.BytesIO()
    small.save(buffer, format="PNG")
    data = buffer.getvalue()
    if len(data) > MAX_FRAME_BYTES:
        raise ImportRejected("Media preview exceeds its size limit.")
    return MediaFrame(seconds, data, hashlib.sha256(data).hexdigest())


def ocr(
    image: Image.Image,
    workspace: Path,
    executable: str | None,
    budget: TextBudget,
    reference: str,
    deadline: float,
) -> str | None:
    if executable is None:
        return "OCR unavailable: a trusted Tesseract runtime is not configured or installed."
    input_path = workspace / "ocr-input.png"
    image.save(input_path, format="PNG")
    text = (
        run_tool(
            [executable, str(input_path), "stdout", "-l", "eng", "--psm", "3"],
            deadline,
        )
        .decode("utf-8", "replace")
        .strip()
    )
    budget.add(reference, text)
    return (
        None
        if text
        else "No text was recognised; this does not prove that the image contains no text."
    )
