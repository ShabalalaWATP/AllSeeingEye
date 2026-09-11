"""Bounded image metadata/OCR and honest capability gaps for private media."""

import io
import json
import pickle
import shutil
from pathlib import Path

import pytest
from PIL import Image

from ase.adapters.research_imports.models import ImportRejected
from ase.adapters.research_media import MediaTools, extract_media, images, video
from ase.adapters.research_media.models import MAX_PIXELS
from ase.adapters.research_media.worker_protocol import encode_media_result, validate_media_result
from media_helpers import synthetic_image


def test_image_metadata_preview_and_verification_leads_are_not_authenticity_claims() -> None:
    result = extract_media(synthetic_image(metadata=True), "sample.png", MediaTools())
    metadata = dict(result.metadata)
    assert metadata["camera_make"] == "Synthetic camera"
    assert metadata["software"] == "Synthetic editor"
    assert any("OCR unavailable" in value for value in result.limitations)
    assert any("does not establish authenticity" in value for value in result.limitations)
    assert any("editable claims" in value for value in result.verification_leads)
    with Image.open(io.BytesIO(result.frames[0].png)) as preview:
        assert max(preview.size) == 512 and not preview.getexif()
        assert not preview.info
    assert b"Private EXIF" not in result.frames[0].png
    assert pickle.loads(pickle.dumps(result)) == result  # noqa: S301
    encoded = json.dumps(encode_media_result(result)).encode()
    assert validate_media_result(encoded, "sample.png", result.sha256) == result


def test_real_local_tesseract_recognises_synthetic_text() -> None:
    executable = shutil.which("tesseract")
    if executable is None:
        pytest.skip("Optional local Tesseract runtime unavailable")
    result = extract_media(synthetic_image(), "test.png", MediaTools(tesseract=executable))
    assert any("SYNTHETIC RAIL TEST 2026" in unit.text for unit in result.units)


@pytest.mark.parametrize(
    "filename",
    ["../photo.png", "a\\photo.png", "C:photo.png", "photo\n.png", "a" * 121, "photo.svg"],
)
def test_unsafe_or_unsupported_media_labels_are_rejected(filename: str) -> None:
    with pytest.raises(ImportRejected):
        extract_media(synthetic_image(), filename, MediaTools())


@pytest.mark.parametrize(
    "data",
    [b"", b"broken secret bytes", b"x" * (8 * 1024 * 1024 + 1)],
    ids=["empty", "malformed", "oversized"],
)
def test_empty_malformed_or_oversized_media_is_rejected_without_echo(data: bytes) -> None:
    with pytest.raises(ImportRejected) as error:
        extract_media(data, "test.png", MediaTools())
    assert "secret" not in str(error.value)


def test_image_type_and_dimension_limits_precede_ocr(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ImportRejected, match="filename type"):
        extract_media(synthetic_image(), "mislabelled.jpg", MediaTools())
    monkeypatch.setattr(images, "MAX_PIXELS", 10)
    with pytest.raises(ImportRejected, match="decoding limits") as error:
        extract_media(synthetic_image(), "oversized.png", MediaTools())
    assert "8 megapixels and 8,192 pixels per edge" in str(error.value)
    assert Image.MAX_IMAGE_PIXELS != 10


def test_animated_image_is_rejected() -> None:
    output = io.BytesIO()
    first = Image.new("RGB", (32, 32), "red")
    first.save(
        output, format="PNG", save_all=True, append_images=[Image.new("RGB", (32, 32), "blue")]
    )
    with pytest.raises(ImportRejected, match="animation") as error:
        extract_media(output.getvalue(), "animated.png", MediaTools())
    assert "static PNG, JPEG or WebP (no animation), up to 8 MiB" in str(error.value)


def test_ocr_receives_sanitised_local_image_and_fixed_arguments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_tool(argv: list[str], deadline: float) -> bytes:
        calls.append(argv)
        with Image.open(argv[1]) as image:
            assert not image.getexif()
        return b"Synthetic OCR passage"

    monkeypatch.setattr(images, "run_tool", fake_tool)
    monkeypatch.setattr("ase.adapters.research_media.trusted_tool", lambda value, name: value)
    result = extract_media(
        synthetic_image(metadata=True), "user-name.png", MediaTools(tesseract="trusted-tesseract")
    )
    assert calls[0][2:] == ["stdout", "-l", "eng", "--psm", "3"]
    assert "user-name" not in calls[0][1]
    assert not Path(calls[0][1]).exists()
    assert result.units[0].text == "Synthetic OCR passage"


def test_missing_video_runtime_produces_no_fabricated_frames_or_metadata() -> None:
    result = extract_media(b"synthetic video bytes", "sample.mp4", MediaTools())
    assert not result.frames and not result.metadata and not result.units
    assert any("Video extraction unavailable" in value for value in result.limitations)


def test_video_playlists_and_fake_containers_are_rejected_before_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("ase.adapters.research_media.trusted_tool", lambda value, name: value)
    with pytest.raises(ImportRejected, match="supported MP4/MOV/WebM container"):
        extract_media(
            b"#EXTM3U\nhttps://private.example/video",
            "fake.mp4",
            MediaTools(ffmpeg="ffmpeg", ffprobe="ffprobe"),
        )


def test_video_uses_local_protocols_fixed_format_and_three_bounded_samples(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []
    frame = synthetic_image()

    def fake_tool(argv: list[str], deadline: float, **kwargs: int) -> bytes:
        calls.append(argv)
        if argv[0] == "trusted-ffprobe":
            return (
                b'{"streams":[{"codec_name":"h264","width":1100,"height":220}],'
                b'"format":{"duration":"9"}}'
            )
        return frame

    monkeypatch.setattr(video, "run_tool", fake_tool)
    monkeypatch.setattr("ase.adapters.research_media.trusted_tool", lambda value, name: value)
    result = extract_media(
        b"\x00\x00\x00\x18ftyp" + b"synthetic",
        "sample.mp4",
        MediaTools(ffmpeg="trusted-ffmpeg", ffprobe="trusted-ffprobe"),
    )
    assert len(calls) == 4 and [frame.seconds for frame in result.frames] == [0, 3, 6]
    assert dict(result.metadata)["duration_seconds"] == "9.0"
    for argv in calls:
        assert argv[argv.index("-protocol_whitelist") + 1] == "file,pipe"
        assert argv[argv.index("-enable_drefs") + 1] == "0"
        assert argv[argv.index("-use_absolute_path") + 1] == "0"
    assert all(len(frame.png) < 1024 * 1024 for frame in result.frames)


@pytest.mark.parametrize(
    "metadata",
    [
        {},
        {"streams": []},
        {"streams": [{"width": MAX_PIXELS, "height": 2}], "format": {"duration": "1"}},
        {"streams": [{"width": 20, "height": 20}], "format": {"duration": "nan"}},
    ],
)
def test_invalid_video_metadata_is_rejected(
    monkeypatch: pytest.MonkeyPatch, metadata: dict[str, object]
) -> None:
    monkeypatch.setattr(video, "run_tool", lambda *args, **kwargs: json.dumps(metadata).encode())
    monkeypatch.setattr("ase.adapters.research_media.trusted_tool", lambda value, name: value)
    with pytest.raises(ImportRejected, match="metadata exceed"):
        extract_media(
            b"\x00\x00\x00\x18ftyp" + b"synthetic",
            "sample.mp4",
            MediaTools(ffmpeg="ffmpeg", ffprobe="ffprobe"),
        )
