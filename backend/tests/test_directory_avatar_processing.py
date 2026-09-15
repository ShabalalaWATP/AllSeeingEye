"""Avatar decoding is bounded, strips metadata and rejects unsupported or hostile files."""

from __future__ import annotations

import io
import struct
import zlib

import pytest
from PIL import Image
from PIL.PngImagePlugin import PngInfo

from ase.adapters.directory_avatar import PillowAvatarProcessor, normalise_avatar
from ase.domain.directory_avatar import AVATAR_EDGE, MAX_AVATAR_UPLOAD_BYTES
from ase.domain.errors import InvalidRequest

SECRET = "Secret-Camera-Owner-51.5N"


def _encode(image: Image.Image, fmt: str, **options: object) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format=fmt, **options)
    return buffer.getvalue()


def _exif() -> Image.Exif:
    exif = Image.Exif()
    exif[0x013B] = SECRET  # Artist
    exif[0x010F] = SECRET  # Make
    exif[0x0112] = 6  # Orientation: rotate 90 degrees clockwise when displayed
    return exif


def test_jpeg_is_reencoded_as_square_webp_without_metadata() -> None:
    source = Image.new("RGB", (400, 200), (200, 30, 30))
    data = _encode(source, "JPEG", exif=_exif(), comment=SECRET.encode())
    assert SECRET.encode() in data

    avatar = normalise_avatar(data)

    assert avatar.content_type == "image/webp"
    assert (avatar.width, avatar.height) == (AVATAR_EDGE, AVATAR_EDGE)
    assert SECRET.encode() not in avatar.content
    with Image.open(io.BytesIO(avatar.content)) as decoded:
        assert decoded.format == "WEBP"
        assert decoded.size == (AVATAR_EDGE, AVATAR_EDGE)
        assert len(decoded.getexif()) == 0
        assert "exif" not in decoded.info
        assert "icc_profile" not in decoded.info
        assert "xmp" not in decoded.info


def test_png_with_transparency_and_text_chunks_is_accepted_cleanly() -> None:
    info = PngInfo()
    info.add_text("Author", SECRET)
    source = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    data = _encode(source, "PNG", pnginfo=info, exif=_exif())

    avatar = normalise_avatar(data)

    assert SECRET.encode() not in avatar.content
    with Image.open(io.BytesIO(avatar.content)) as decoded:
        assert "A" in decoded.getbands()
        assert not getattr(decoded, "text", {})


def test_polyglot_trailing_payload_is_discarded() -> None:
    payload = b"<html><script>alert(1)</script></html>PK\x03\x04zip-member"
    data = _encode(Image.new("RGB", (32, 32), "blue"), "PNG") + payload

    avatar = normalise_avatar(data)

    assert b"<script>" not in avatar.content
    assert b"PK\x03\x04" not in avatar.content


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"not an image at all",
        b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>",
        b"\x89PNG\r\n\x1a\n" + b"\x00" * 64,
        b"GIF89a" + b"\x00" * 64,
    ],
    ids=["empty", "text", "svg", "corrupt-png", "gif-header"],
)
def test_garbage_and_unsupported_bytes_are_rejected(data: bytes) -> None:
    with pytest.raises(InvalidRequest):
        normalise_avatar(data)


def test_real_but_unsupported_formats_are_rejected() -> None:
    for fmt in ("GIF", "BMP", "TIFF"):
        with pytest.raises(InvalidRequest):
            normalise_avatar(_encode(Image.new("RGB", (16, 16)), fmt))


def test_truncated_image_is_rejected() -> None:
    data = _encode(Image.effect_noise((128, 128), 64).convert("RGB"), "PNG")
    with pytest.raises(InvalidRequest):
        normalise_avatar(data[: len(data) // 2])


def test_oversize_upload_is_rejected_before_decoding() -> None:
    with pytest.raises(InvalidRequest):
        normalise_avatar(b"\xff\xd8\xff" + b"\x00" * MAX_AVATAR_UPLOAD_BYTES)


@pytest.mark.parametrize("size", [(4097, 1), (1, 4097), (4000, 4001)])
def test_huge_declared_dimensions_are_rejected(size: tuple[int, int]) -> None:
    # Solid colour compresses to a few kilobytes, so the byte cap alone would not stop it.
    data = _encode(Image.new("L", size, 0), "PNG", optimize=True)
    assert len(data) < MAX_AVATAR_UPLOAD_BYTES
    with pytest.raises(InvalidRequest):
        normalise_avatar(data)


def test_decompression_bomb_header_is_rejected_without_loading_pixels() -> None:
    # Rewrite a small PNG's IHDR to declare a 60,000 x 60,000 canvas.
    data = bytearray(_encode(Image.new("L", (1, 1), 0), "PNG"))
    ihdr = struct.pack(">IIBBBBB", 60_000, 60_000, 8, 0, 0, 0, 0)
    data[16:29] = ihdr
    data[29:33] = struct.pack(">I", zlib.crc32(b"IHDR" + ihdr))
    with pytest.raises(InvalidRequest):
        normalise_avatar(bytes(data))


def test_animated_images_are_rejected() -> None:
    frames = [Image.new("RGB", (16, 16), colour) for colour in ("red", "blue")]
    for fmt in ("PNG", "WEBP"):
        data = _encode(frames[0], fmt, save_all=True, append_images=frames[1:], duration=100)
        with pytest.raises(InvalidRequest):
            normalise_avatar(data)


async def test_processor_runs_off_the_event_loop() -> None:
    data = _encode(Image.new("CMYK", (50, 80), (0, 0, 0, 0)), "JPEG")
    avatar = await PillowAvatarProcessor().process(data)
    assert avatar.sha256 and len(avatar.sha256) == 64
