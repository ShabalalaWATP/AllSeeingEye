"""Media extraction entrypoint, only for the killable resource-bounded research worker."""

import hashlib
import time
from pathlib import Path, PurePath
from tempfile import TemporaryDirectory

from ase.adapters.research_imports.models import MAX_UPLOAD_BYTES, ImportRejected, TextBudget
from ase.adapters.research_media.images import decode_image, ocr, preview
from ase.adapters.research_media.models import (
    COMMON_LIMITATIONS,
    VERIFICATION_LEADS,
    MediaExtractionResult,
    MediaTools,
)
from ase.adapters.research_media.tools import trusted_tool
from ase.adapters.research_media.video import extract_video

__all__ = ["MediaExtractionResult", "MediaTools", "extract_media"]

MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
}


def extract_media(data: bytes, filename: str, tools: MediaTools) -> MediaExtractionResult:
    """Accept transient bytes and a label, never a user-selected input path, URL or command."""
    if not data or len(data) > MAX_UPLOAD_BYTES:
        raise ImportRejected("Media is empty or exceeds the 8 MiB upload limit.")
    if (
        not filename
        or len(filename) > 120
        or any(ord(char) < 32 for char in filename)
        or any(char in filename for char in "/\\:")
    ):
        raise ImportRejected("Use a plain filename of at most 120 characters.")
    extension = PurePath(filename).suffix.lower()
    if extension not in MEDIA_TYPES:
        raise ImportRejected("Supported media are JPEG, PNG, WebP, MP4, MOV and WebM.")
    tesseract = trusted_tool(tools.tesseract, "tesseract")
    ffmpeg = trusted_tool(tools.ffmpeg, "ffmpeg")
    ffprobe = trusted_tool(tools.ffprobe, "ffprobe")
    budget = TextBudget()
    deadline = time.monotonic() + 20
    limitations = list(COMMON_LIMITATIONS)
    try:
        with TemporaryDirectory(prefix="ase-media-") as directory:
            workspace = Path(directory)
            if extension in {".mp4", ".mov", ".webm"}:
                metadata, frames, limits = extract_video(
                    data,
                    extension,
                    workspace,
                    ffmpeg,
                    ffprobe,
                    tesseract,
                    budget,
                    deadline,
                )
                limitations.extend(limits)
            else:
                image, metadata = decode_image(data)
                expected_format = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".webp": "WEBP"}
                if dict(metadata)["format"] != expected_format[extension]:
                    raise ImportRejected("Image content does not match its filename type.")
                frames = (preview(image),)
                limit = ocr(image, workspace, tesseract, budget, "Image OCR", deadline)
                if limit:
                    limitations.append(limit)
            for key, value in metadata:
                budget.add(f"Media metadata: {key}", value)
    except ImportRejected:
        raise
    except Exception:
        raise ImportRejected("The media is malformed or processing is unavailable.") from None
    return MediaExtractionResult(
        filename,
        MEDIA_TYPES[extension],
        hashlib.sha256(data).hexdigest(),
        tuple(budget.units),
        tuple(limitations),
        metadata,
        frames,
        VERIFICATION_LEADS,
    )
