"""Validate bounded derivative PNG envelopes without invoking an image parser in the server."""

import hashlib
import math

from ase.application.ports.research_inputs import MAX_PREVIEW_BYTES, InputPreviewFrame
from ase.domain.errors import InvalidRequest


def preview_size(frames: tuple[InputPreviewFrame, ...]) -> int:
    total = sum(len(frame.png) for frame in frames)
    if len(frames) > 3 or total > MAX_PREVIEW_BYTES:
        raise InvalidRequest("Extracted media previews exceed their retention budget.")
    for frame in frames:
        data = frame.png
        if (
            not isinstance(data, bytes)
            or len(data) < 24
            or data[:8] != b"\x89PNG\r\n\x1a\n"
            or data[8:16] != b"\x00\x00\x00\x0dIHDR"
            or not 1 <= int.from_bytes(data[16:20], "big") <= 512
            or not 1 <= int.from_bytes(data[20:24], "big") <= 512
            or not math.isfinite(frame.seconds)
            or not 0 <= frame.seconds <= 600
            or hashlib.sha256(data).hexdigest() != frame.sha256
        ):
            raise InvalidRequest("An extracted media preview failed its integrity check.")
    return total + 256 * len(frames)
