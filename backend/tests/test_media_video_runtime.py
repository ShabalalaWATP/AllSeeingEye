"""Optional real FFmpeg decoding uses a short locally generated synthetic video only."""

import shutil
import time
from pathlib import Path

import pytest

from ase.adapters.research_media import MediaTools, extract_media
from ase.adapters.research_media.tools import run_tool
from media_helpers import synthetic_image


def _runtime(name: str) -> str | None:
    installed = shutil.which(name)
    if installed:
        return installed
    root = Path(__file__).resolve().parents[2]
    candidate = (
        root
        / "data"
        / "research-runtime"
        / "ffmpeg-9.0.1"
        / "ffmpeg-9.0.1-essentials_build"
        / "bin"
        / f"{name}.exe"
    )
    return str(candidate) if candidate.is_file() else None


@pytest.mark.parametrize(
    "extension,encoder,codec", [(".mp4", "libx264", "h264"), (".webm", "libvpx-vp9", "vp9")]
)
def test_real_ffmpeg_extracts_three_samples_from_generated_video(
    tmp_path: Path,
    extension: str,
    encoder: str,
    codec: str,
) -> None:
    ffmpeg, ffprobe = _runtime("ffmpeg"), _runtime("ffprobe")
    if not ffmpeg or not ffprobe:
        pytest.skip("Optional trusted local FFmpeg/ffprobe runtime unavailable")
    source = tmp_path / "synthetic.png"
    target = tmp_path / f"synthetic{extension}"
    source.write_bytes(synthetic_image())
    run_tool(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-loop",
            "1",
            "-i",
            str(source),
            "-t",
            "3",
            "-vf",
            "scale=640:128",
            "-c:v",
            encoder,
            "-threads",
            "1",
            "-pix_fmt",
            "yuv420p",
            "-y",
            str(target),
        ],
        time.monotonic() + 10,
    )
    result = extract_media(
        target.read_bytes(), target.name, MediaTools(ffmpeg=ffmpeg, ffprobe=ffprobe)
    )
    assert len(result.frames) == 3
    assert [frame.seconds for frame in result.frames] == [0, 1, 2]
    assert dict(result.metadata)["codec"] == codec
    assert all(frame.png.startswith(b"\x89PNG") for frame in result.frames)
