"""Hostile worker responses cannot widen the media API's output bounds."""

import base64
import hashlib
import json
import struct
import zlib
from collections.abc import Callable
from typing import Any

import pytest

from ase.adapters.research_imports.models import ImportRejected
from ase.adapters.research_media import MediaTools, extract_media
from ase.adapters.research_media.worker_protocol import encode_media_result, validate_media_result
from media_helpers import synthetic_image


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.update(extra="secret"),
        lambda value: value.update(filename="other.png"),
        lambda value: value.update(sha256="fake"),
        lambda value: value.update(media_type="text/html"),
        lambda value: value.update(units=[{"reference": "r", "text": "x"}] * 201),
        lambda value: value.update(units=[{"reference": "r", "text": "x" * 1801}]),
        lambda value: value.update(units=[{"reference": "r", "text": "x" * 1800}] * 112),
        lambda value: value.update(units=[{"reference": "r", "text": "x", "extra": True}]),
        lambda value: value.update(metadata=[["key", "value", "extra"]]),
        lambda value: value.update(metadata=[["key", "value"]] * 17),
        lambda value: value.update(limitations=["x"] * 21),
        lambda value: value.update(verification_leads=["x" * 501]),
        lambda value: value.update(frames=value["frames"] * 4),
        lambda value: value["frames"][0].update(seconds=float("nan")),
        lambda value: value["frames"][0].update(seconds=True),
        lambda value: value["frames"][0].update(png="invalid base64"),
        lambda value: value["frames"][0].update(sha256="mismatch"),
    ],
    ids=[
        "extra",
        "filename",
        "hash",
        "mime",
        "unit-count",
        "unit-length",
        "total-text",
        "unit-fields",
        "metadata-shape",
        "metadata-count",
        "limits",
        "leads",
        "frame-count",
        "nan-time",
        "boolean-time",
        "base64",
        "frame-hash",
    ],
)
def test_invalid_result_is_rejected_without_disclosing_worker_text(
    mutate: Callable[[Any], None],
) -> None:
    result = extract_media(synthetic_image(), "test.png", MediaTools())
    envelope = encode_media_result(result)
    mutate(envelope["result"])
    with pytest.raises(ImportRejected, match="invalid or oversized") as error:
        validate_media_result(json.dumps(envelope).encode(), "test.png", result.sha256)
    assert "secret" not in str(error.value)


@pytest.mark.parametrize("kind", ["dimensions", "crc", "signature"])
def test_png_headers_are_checked_without_decoding_images(kind: str) -> None:
    result = extract_media(synthetic_image(), "test.png", MediaTools())
    envelope: Any = encode_media_result(result)
    frame = envelope["result"]["frames"][0]
    png = bytearray(base64.b64decode(frame["png"]))
    if kind == "dimensions":
        png[16:20] = struct.pack(">I", 100_000)
        png[29:33] = struct.pack(">I", zlib.crc32(png[12:29]))
    elif kind == "crc":
        png[29:33] = b"\x00" * 4
    else:
        png[0] = 0
    frame["png"] = base64.b64encode(png).decode()
    frame["sha256"] = hashlib.sha256(png).hexdigest()
    with pytest.raises(ImportRejected):
        validate_media_result(json.dumps(envelope).encode(), "test.png", result.sha256)


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b"{" * 2000,
        b'{"ok":false,"error":"secret traceback"}',
        b'{"ok":true}',
        b"x" * (4 * 1024 * 1024 + 1),
    ],
    ids=["empty", "nested", "forged-error", "shape", "size"],
)
def test_invalid_envelope_is_sanitised(payload: bytes) -> None:
    with pytest.raises(ImportRejected) as error:
        validate_media_result(payload, "test.png", "digest")
    assert "secret" not in str(error.value)


@pytest.mark.parametrize("code", ["rejected", "resource_limits"])
def test_known_worker_errors_are_safe(code: str) -> None:
    with pytest.raises(ImportRejected, match="rejected or exceeded"):
        validate_media_result(json.dumps({"ok": False, "error": code}).encode(), "test.png", "hash")
