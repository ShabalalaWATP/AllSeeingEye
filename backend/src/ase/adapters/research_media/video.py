"""Local MP4/MOV/WebM metadata and three sampled frames, without network protocols."""

import json
import math
from pathlib import Path

from ase.adapters.research_imports.models import ImportRejected, TextBudget
from ase.adapters.research_media.images import decode_image, ocr, preview
from ase.adapters.research_media.models import (
    MAX_DIMENSION,
    MAX_FRAME_BYTES,
    MAX_FRAMES,
    MAX_PIXELS,
    MAX_VIDEO_SECONDS,
    MediaFrame,
)
from ase.adapters.research_media.tools import run_tool


def extract_video(
    data: bytes,
    extension: str,
    workspace: Path,
    ffmpeg: str | None,
    ffprobe: str | None,
    tesseract: str | None,
    budget: TextBudget,
    deadline: float,
) -> tuple[tuple[tuple[str, str], ...], tuple[MediaFrame, ...], tuple[str, ...]]:
    if ffmpeg is None or ffprobe is None:
        return (
            (),
            (),
            ("Video extraction unavailable: trusted FFmpeg and ffprobe runtimes are required.",),
        )
    if extension in {".mp4", ".mov"} and data[4:8] == b"ftyp":
        format_args = ["-f", "mov", "-enable_drefs", "0", "-use_absolute_path", "0"]
    elif extension == ".webm" and data.startswith(b"\x1aE\xdf\xa3"):
        format_args = ["-f", "matroska"]
    else:
        raise ImportRejected("The upload is not a supported MP4/MOV/WebM container.")
    path = workspace / "input-media.bin"
    path.write_bytes(data)
    # Force the demuxer and disable MOV external references. Network/playlist protocols cannot open.
    input_args = ["-protocol_whitelist", "file,pipe", *format_args, "-i", str(path)]
    raw = run_tool(
        [
            ffprobe,
            "-v",
            "error",
            "-threads",
            "1",
            *input_args,
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=codec_name,width,height:format=duration",
            "-of",
            "json",
        ],
        deadline,
    )
    try:
        result = json.loads(raw)
        stream = result["streams"][0]
        width, height = int(stream["width"]), int(stream["height"])
        duration = float(result["format"]["duration"])
        if (
            min(width, height) < 1
            or width * height > MAX_PIXELS
            or max(width, height) > MAX_DIMENSION
            or not math.isfinite(duration)
            or not 0 < duration <= MAX_VIDEO_SECONDS
        ):
            raise ValueError
        codec = str(stream.get("codec_name") or "unknown")[:80]
    except (ValueError, TypeError, KeyError, IndexError):
        raise ImportRejected(
            "Video dimensions, duration or metadata exceed supported limits."
        ) from None
    metadata = (
        ("width", str(width)),
        ("height", str(height)),
        ("duration_seconds", str(duration)),
        ("codec", codec),
    )
    frames: list[MediaFrame] = []
    limitations = [
        "Three approximate timestamp samples are not a full review or codec keyframe inventory.",
        "Audio, subtitles, hidden tracks and full motion are not analysed; metadata is unverified.",
    ]
    for index in range(MAX_FRAMES):
        seconds = round(duration * index / MAX_FRAMES, 3)
        png = run_tool(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-nostdin",
                "-threads",
                "1",
                "-ss",
                str(seconds),
                *input_args,
                "-map",
                "0:v:0",
                "-an",
                "-sn",
                "-dn",
                "-frames:v",
                "1",
                "-vf",
                "scale=512:512:force_original_aspect_ratio=decrease",
                "-threads",
                "1",
                "-f",
                "image2pipe",
                "-vcodec",
                "png",
                "pipe:1",
            ],
            deadline,
            max_output=MAX_FRAME_BYTES,
        )
        image, _ = decode_image(png)
        frames.append(preview(image, seconds))
        budget.add(
            f"Video sample at approximately {seconds:g} seconds",
            "Sampled frame; visual verification required.",
        )
        limitation = ocr(
            image,
            workspace,
            tesseract,
            budget,
            f"Video OCR at approximately {seconds:g} seconds",
            deadline,
        )
        if limitation and limitation not in limitations:
            limitations.append(limitation)
    return metadata, tuple(frames), tuple(limitations)
