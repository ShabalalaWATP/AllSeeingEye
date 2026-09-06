"""Strict bounded JSON boundary between the disposable media worker and API process."""

import base64
import hashlib
import json
import math
import struct
import zlib
from pathlib import PurePath
from typing import Any

from ase.adapters.research_imports.models import (
    MAX_TEXT_CHARS,
    MAX_UNIT_CHARS,
    MAX_UNITS,
    ExtractedUnit,
    ImportRejected,
)
from ase.adapters.research_media import MEDIA_TYPES
from ase.adapters.research_media.models import (
    MAX_FRAME_BYTES,
    MAX_FRAMES,
    MediaExtractionResult,
    MediaFrame,
)

MAX_RESPONSE_BYTES = 4 * 1024 * 1024
RESULT_KEYS = {
    "filename",
    "media_type",
    "sha256",
    "units",
    "limitations",
    "metadata",
    "frames",
    "verification_leads",
}


def encode_media_result(result: MediaExtractionResult) -> dict[str, object]:
    return {
        "ok": True,
        "result": {
            "filename": result.filename,
            "media_type": result.media_type,
            "sha256": result.sha256,
            "units": [{"reference": unit.reference, "text": unit.text} for unit in result.units],
            "limitations": list(result.limitations),
            "metadata": [list(pair) for pair in result.metadata],
            "verification_leads": list(result.verification_leads),
            "frames": [
                {
                    "seconds": frame.seconds,
                    "png": base64.b64encode(frame.png).decode("ascii"),
                    "sha256": frame.sha256,
                }
                for frame in result.frames
            ],
        },
    }


def _text(value: Any, maximum: int) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise ValueError
    return value


def _strings(value: Any, count: int, maximum: int) -> tuple[str, ...]:
    if not isinstance(value, list) or len(value) > count:
        raise ValueError
    return tuple(_text(item, maximum) for item in value)


def _frame(value: Any) -> MediaFrame:
    if not isinstance(value, dict) or set(value) != {"seconds", "png", "sha256"}:
        raise ValueError
    seconds = value["seconds"]
    if type(seconds) not in {int, float} or not math.isfinite(seconds) or not 0 <= seconds <= 600:
        raise ValueError
    encoded = _text(value["png"], ((MAX_FRAME_BYTES + 2) // 3) * 4)
    png = base64.b64decode(encoded, validate=True)
    if not 33 <= len(png) <= MAX_FRAME_BYTES or png[:16] != b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR":
        raise ValueError
    width, height = struct.unpack(">II", png[16:24])
    if not (0 < width <= 512 and 0 < height <= 512) or png[24:29] != b"\x08\x02\x00\x00\x00":
        raise ValueError
    if zlib.crc32(png[12:29]) != struct.unpack(">I", png[29:33])[0]:
        raise ValueError
    digest = hashlib.sha256(png).hexdigest()
    if value["sha256"] != digest:
        raise ValueError
    return MediaFrame(float(seconds), png, digest)


def _result(value: Any, filename: str, expected_hash: str) -> MediaExtractionResult:
    if not isinstance(value, dict) or set(value) != RESULT_KEYS:
        raise ValueError
    if value["filename"] != filename or value["sha256"] != expected_hash:
        raise ValueError
    if value["media_type"] != MEDIA_TYPES.get(PurePath(filename).suffix.lower()):
        raise ValueError
    raw_units = value["units"]
    if not isinstance(raw_units, list) or len(raw_units) > MAX_UNITS:
        raise ValueError
    units = []
    for unit in raw_units:
        if not isinstance(unit, dict) or set(unit) != {"reference", "text"}:
            raise ValueError
        units.append(
            ExtractedUnit(_text(unit["reference"], 200), _text(unit["text"], MAX_UNIT_CHARS))
        )
    if sum(len(unit.text) for unit in units) > MAX_TEXT_CHARS:
        raise ValueError
    metadata = value["metadata"]
    if not isinstance(metadata, list) or len(metadata) > 16:
        raise ValueError
    pairs: list[tuple[str, str]] = []
    for pair in metadata:
        if not isinstance(pair, list) or len(pair) != 2:
            raise ValueError
        pairs.append((_text(pair[0], 80), _text(pair[1], 200)))
    raw_frames = value["frames"]
    if not isinstance(raw_frames, list) or len(raw_frames) > MAX_FRAMES:
        raise ValueError
    frames = tuple(_frame(frame) for frame in raw_frames)
    if tuple(frame.seconds for frame in frames) != tuple(sorted(frame.seconds for frame in frames)):
        raise ValueError
    return MediaExtractionResult(
        filename,
        value["media_type"],
        expected_hash,
        tuple(units),
        _strings(value["limitations"], 20, 500),
        tuple(pairs),
        frames,
        _strings(value["verification_leads"], 10, 500),
    )


def validate_media_result(data: bytes, filename: str, expected_hash: str) -> MediaExtractionResult:
    """Validate structure and PNG headers only; no untrusted decoder runs in the API process."""
    try:
        if not data or len(data) > MAX_RESPONSE_BYTES:
            raise ValueError
        envelope = json.loads(data)
        if isinstance(envelope, dict) and envelope.get("ok") is False:
            if set(envelope) != {"ok", "error"} or envelope["error"] not in {
                "rejected",
                "resource_limits",
            }:
                raise ValueError
            raise ImportRejected("Media processing was rejected or exceeded resource limits.")
        if (
            not isinstance(envelope, dict)
            or set(envelope) != {"ok", "result"}
            or envelope["ok"] is not True
        ):
            raise ValueError
        return _result(envelope["result"], filename, expected_hash)
    except ImportRejected:
        raise
    except Exception:
        raise ImportRejected("Media worker returned invalid or oversized output.") from None
