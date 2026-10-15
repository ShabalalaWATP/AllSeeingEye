"""Native regression fixtures generated locally, without hostile bitstreams or network."""

import time
from pathlib import Path

from ase.adapters.research_media.tools import run_tool


def generate_video(
    ffmpeg: str,
    target: Path,
    encoder: str,
    *,
    audio: str | None = None,
    secondary: str | None = None,
) -> bytes:
    inputs = ["-f", "lavfi", "-i", "testsrc2=size=320x192:rate=3"]
    mapping = ["-map", "0:v:0"]
    options = ["-c:v:0", encoder, "-pix_fmt:v:0", "yuv420p"]
    if encoder == "cfhd":
        options[-1] = "yuv422p10le"
    if audio:
        inputs += ["-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000"]
        mapping += ["-map", "1:a:0"]
        options += ["-c:a", audio]
    if secondary:
        mapping += ["-map", "0:v:0"]
        options += ["-c:v:1", secondary, "-pix_fmt:v:1", "yuv422p10le"]
    if encoder == "libx265":
        options += ["-x265-params", "pools=1:frame-threads=1"]
    if encoder == "libaom-av1":
        options += ["-cpu-used", "8"]
    run_tool(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            *inputs,
            "-t",
            "3",
            *mapping,
            *options,
            "-threads",
            "1",
            "-y",
            str(target),
        ],
        time.monotonic() + 10,
    )
    return target.read_bytes()
