"""Small, re-encoded directory avatars stored one per account."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Final
from uuid import UUID

MAX_AVATAR_UPLOAD_BYTES: Final = 2 * 1024 * 1024
MAX_AVATAR_STORED_BYTES: Final = 256 * 1024
AVATAR_EDGE: Final = 256
# Decoding limits apply before pixel data is loaded, so a small file cannot
# declare a huge canvas and exhaust memory.
MAX_AVATAR_SOURCE_EDGE: Final = 4096
MAX_AVATAR_SOURCE_PIXELS: Final = 16_000_000
AVATAR_CONTENT_TYPES: Final = frozenset({"image/webp", "image/png"})


@dataclass(frozen=True, slots=True)
class ProcessedAvatar:
    """Metadata-free image bytes produced by the avatar processor."""

    content: bytes
    content_type: str
    sha256: str
    width: int
    height: int

    def __post_init__(self) -> None:
        if not self.content or len(self.content) > MAX_AVATAR_STORED_BYTES:
            raise ValueError("Processed avatar exceeds its stored size limit")
        if self.content_type not in AVATAR_CONTENT_TYPES:
            raise ValueError("Processed avatar content type is unsupported")
        if not (0 < self.width <= AVATAR_EDGE and 0 < self.height <= AVATAR_EDGE):
            raise ValueError("Processed avatar dimensions are out of bounds")


@dataclass(frozen=True, slots=True)
class DirectoryAvatar:
    user_id: UUID
    image: ProcessedAvatar
    updated_at: datetime
