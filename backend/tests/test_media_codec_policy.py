"""Untrusted containers cannot select unreviewed native decoders during probing."""

import json

import pytest

from ase.adapters.research_imports.models import ImportRejected
from ase.adapters.research_media import MediaTools, extract_media, video
from media_helpers import synthetic_image


@pytest.mark.parametrize("extension,header", [(".mov", b"0000ftyp"), (".webm", b"\x1aE\xdf\xa3")])
def test_decoder_policy_precedes_probe_and_frame_input(
    monkeypatch: pytest.MonkeyPatch, extension: str, header: bytes
) -> None:
    calls: list[list[str]] = []

    def tool(argv: list[str], deadline: float, **kwargs: int) -> bytes:
        calls.append(argv)
        position = argv.index("-codec_whitelist")
        assert position < argv.index("-i")
        allowed = set(argv[position + 1].split(","))
        assert {"h264", "hevc", "vp8", "vp9", "av1", "aac", "opus"} <= allowed
        assert not allowed & {"cfhd", "rasc", "adpcm_adx", "mace6", "png", "all", "*"}
        if argv[0] == "ffprobe":
            return json.dumps(
                {
                    "streams": [{"codec_name": "h264", "width": 100, "height": 50}],
                    "format": {"duration": "3"},
                }
            ).encode()
        return synthetic_image()

    monkeypatch.setattr(video, "run_tool", tool)
    monkeypatch.setattr("ase.adapters.research_media.trusted_tool", lambda value, name: value)
    result = extract_media(
        header + b"synthetic", "test" + extension, MediaTools(ffmpeg="ffmpeg", ffprobe="ffprobe")
    )
    assert len(calls) == 4
    assert len(result.frames) == 3


@pytest.mark.parametrize("codec", ["cfhd", "rasc", "png", "unknown", "", None, 42])
def test_unsupported_metadata_never_reaches_frame_extraction(
    monkeypatch: pytest.MonkeyPatch, codec: object
) -> None:
    calls: list[str] = []

    def tool(argv: list[str], deadline: float, **kwargs: int) -> bytes:
        calls.append(argv[0])
        return json.dumps(
            {
                "streams": [{"codec_name": codec, "width": 100, "height": 50}],
                "format": {"duration": "3"},
            }
        ).encode()

    monkeypatch.setattr(video, "run_tool", tool)
    monkeypatch.setattr("ase.adapters.research_media.trusted_tool", lambda value, name: value)
    with pytest.raises(ImportRejected, match="video codec"):
        extract_media(
            b"0000ftypsynthetic", "test.mov", MediaTools(ffmpeg="ffmpeg", ffprobe="ffprobe")
        )
    assert calls == ["ffprobe"]
