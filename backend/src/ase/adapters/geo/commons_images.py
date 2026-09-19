"""Bounded Wikimedia raster downloads and Pillow decoding for operator imports."""

from __future__ import annotations

import io
import warnings
from typing import Any

import httpx
from PIL import Image, ImageDraw, UnidentifiedImageError

MAX_SOURCE_EDGE = 4_096
MAX_SOURCE_PIXELS = 16_000_000
_FORMATS = ("JPEG", "PNG", "WEBP", "GIF")


def download_raster(
    client: httpx.Client,
    url: str,
    *,
    params: dict[str, Any],
    max_bytes: int,
) -> bytes:
    body = bytearray()
    with client.stream(
        "GET",
        url,
        params=params,
        headers={"Accept-Encoding": "identity"},
        follow_redirects=True,
    ) as response:
        response.raise_for_status()
        encoding = response.headers.get("content-encoding", "identity").casefold()
        if encoding not in ("", "identity"):
            raise ValueError("Wikimedia image used an unsupported content encoding")
        declared = response.headers.get("content-length")
        if declared is not None:
            try:
                length = int(declared)
            except ValueError:
                raise ValueError("Wikimedia image has an invalid content length") from None
            if length > max_bytes:
                raise ValueError("Wikimedia image exceeded its byte limit")
        if response.is_stream_consumed:
            body.extend(response.content)
        else:
            for chunk in response.iter_raw():
                body.extend(chunk)
                if len(body) > max_bytes:
                    raise ValueError("Wikimedia image exceeded its byte limit")
        if len(body) > max_bytes:
            raise ValueError("Wikimedia image exceeded its byte limit")
    return bytes(body)


def decode_raster(data: bytes) -> Image.Image:
    """Decode one bounded canvas and intentionally keep only an animation's first frame."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data), formats=_FORMATS) as source:
                width, height = source.size
                if (
                    width < 1
                    or height < 1
                    or max(width, height) > MAX_SOURCE_EDGE
                    or width * height > MAX_SOURCE_PIXELS
                ):
                    raise ValueError("Wikimedia image canvas exceeded its limit")
                source.seek(0)
                source.load()
                return source.convert("RGB")
    except (
        UnidentifiedImageError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ):
        raise ValueError("Wikimedia image could not be decoded safely") from None


def circular_portrait_png(data: bytes, size: int) -> bytes:
    picture = decode_raster(data)
    side = min(picture.size)
    left, top = (picture.width - side) // 2, max(0, (picture.height - side) // 4)
    square = picture.crop((left, top, left + side, top + side)).resize(
        (size, size), Image.Resampling.LANCZOS
    )
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    circular = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    circular.paste(square, (0, 0), mask)
    buffer = io.BytesIO()
    circular.quantize(colors=96, method=Image.Quantize.FASTOCTREE).save(
        buffer, format="PNG", optimize=True
    )
    return buffer.getvalue()
