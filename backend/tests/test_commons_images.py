"""Wikimedia raster downloads and decoding stay within byte and canvas limits."""

from __future__ import annotations

import io

import httpx
import pytest
from PIL import Image

from ase.adapters.geo import commons_images


def _png(width: int = 10, height: int = 10) -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (width, height), "red").save(output, format="PNG")
    return output.getvalue()


@pytest.mark.parametrize(
    ("headers", "body"),
    [
        ({"content-length": "101"}, _png()),
        ({"content-encoding": "gzip"}, _png()),
        ({}, b"x" * 101),
    ],
    ids=("declared-oversize", "encoded", "actual-oversize"),
)
def test_download_rejects_declared_encoded_and_actual_oversize_bodies(
    headers: dict[str, str], body: bytes
) -> None:
    with (
        httpx.Client(
            transport=httpx.MockTransport(
                lambda _request: httpx.Response(200, headers=headers, stream=httpx.ByteStream(body))
            )
        ) as client,
        pytest.raises(ValueError),
    ):
        commons_images.download_raster(
            client, "https://commons.wikimedia.org/x", params={}, max_bytes=100
        )


def test_decode_rejects_large_canvas_and_decompression_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(commons_images, "MAX_SOURCE_EDGE", 5)
    with pytest.raises(ValueError, match="canvas"):
        commons_images.decode_raster(_png())

    monkeypatch.setattr(commons_images, "MAX_SOURCE_EDGE", 4_096)
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 1)
    with pytest.raises(ValueError, match="safely"):
        commons_images.decode_raster(_png())
