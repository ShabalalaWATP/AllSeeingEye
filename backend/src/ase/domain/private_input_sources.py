"""Exact private-source identity shared by intake admission and media extraction."""

from pathlib import PurePath
from types import MappingProxyType

MEDIA_TYPES = MappingProxyType(
    {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".mp4": "video/mp4",
        ".mov": "video/quicktime",
        ".webm": "video/webm",
    }
)
PRIVATE_SOURCE_IDS = frozenset({"research_import", "research_media"})


def private_input_source(filename: str, media_type: str = "") -> str:
    """Classify before body reads; retained receipts also carry a verified media type."""
    if PurePath(filename).suffix.lower() in MEDIA_TYPES or media_type.startswith(
        ("image/", "video/")
    ):
        return "research_media"
    return "research_import"
