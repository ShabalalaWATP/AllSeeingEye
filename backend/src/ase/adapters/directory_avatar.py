"""Pillow avatar normalisation: bounded decode, metadata removal and re-encoding."""

from __future__ import annotations

import asyncio
import hashlib
import io
import threading
import warnings

from PIL import Image, ImageOps

from ase.domain.directory_avatar import (
    AVATAR_EDGE,
    MAX_AVATAR_SOURCE_EDGE,
    MAX_AVATAR_SOURCE_PIXELS,
    MAX_AVATAR_UPLOAD_BYTES,
    ProcessedAvatar,
)
from ase.domain.errors import InvalidRequest

AVATAR_REQUIREMENTS = (
    "Use a static JPEG, PNG or WebP image up to 2 MB and at most 4,096 pixels per edge."
)
_ACCEPTED_FORMATS = ("JPEG", "PNG", "WEBP")
# A permitted source canvas can occupy about 64 MB once decoded; bound parallel work.
# A thread semaphore is loop-independent and is held only inside the worker thread.
_DECODE_SLOTS = threading.BoundedSemaphore(2)


def _rejected() -> InvalidRequest:
    # A single generic message avoids acting as a decoder oracle for crafted files.
    return InvalidRequest("The avatar image could not be accepted. " + AVATAR_REQUIREMENTS)


def _normalise_bounded(data: bytes) -> ProcessedAvatar:
    with _DECODE_SLOTS:
        return normalise_avatar(data)


def normalise_avatar(data: bytes) -> ProcessedAvatar:
    """Return a square, metadata-free WebP rendering of an uploaded image."""

    if not data or len(data) > MAX_AVATAR_UPLOAD_BYTES:
        raise _rejected()
    try:
        with warnings.catch_warnings():
            # Pillow's own bomb heuristic becomes a hard failure rather than a log line.
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data), formats=_ACCEPTED_FORMATS) as source:
                width, height = source.size
                # ``Image.open`` reads headers only; check the declared canvas before
                # any pixel data is decoded.
                if (
                    width < 1
                    or height < 1
                    or max(width, height) > MAX_AVATAR_SOURCE_EDGE
                    or width * height > MAX_AVATAR_SOURCE_PIXELS
                    or getattr(source, "is_animated", False)
                    or getattr(source, "n_frames", 1) != 1
                ):
                    raise _rejected()
                source.load()
                oriented = ImageOps.exif_transpose(source)
                has_alpha = "A" in oriented.getbands() or "transparency" in oriented.info
                mode = "RGBA" if has_alpha else "RGB"
                pixels = oriented.convert(mode)
    except InvalidRequest:
        raise
    except Exception:
        raise _rejected() from None
    fitted = ImageOps.fit(pixels, (AVATAR_EDGE, AVATAR_EDGE), Image.Resampling.LANCZOS)
    # Rebuilding from raw pixels drops EXIF, ICC profiles, XMP, comments and any
    # bytes appended to a polyglot file.
    clean = Image.frombytes(mode, fitted.size, fitted.tobytes())
    buffer = io.BytesIO()
    clean.save(buffer, format="WEBP", quality=85, method=4)
    content = buffer.getvalue()
    try:
        return ProcessedAvatar(
            content=content,
            content_type="image/webp",
            sha256=hashlib.sha256(content).hexdigest(),
            width=clean.width,
            height=clean.height,
        )
    except ValueError:
        raise _rejected() from None


class PillowAvatarProcessor:
    """Runs CPU-bound decoding off the event loop."""

    async def process(self, data: bytes) -> ProcessedAvatar:
        return await asyncio.to_thread(_normalise_bounded, data)
