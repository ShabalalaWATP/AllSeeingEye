"""Fixed-file JSON IPC entrypoint for ``python -I -m ase.adapters.research_worker``.

The parent chooses a private temporary working directory. No path or executable
is accepted from document content; stdout/stderr are discarded by the parent.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

from ase.adapters.research_worker.limits import ResourceLimitUnavailable, apply_resource_limits

MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_OUTPUT_BYTES = 1024 * 1024
MAX_MEDIA_OUTPUT_BYTES = 4 * 1024 * 1024


def _reply(value: dict[str, object], maximum: int = MAX_OUTPUT_BYTES) -> None:
    output = json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
    if len(output) > maximum:
        output = b'{"ok":false,"error":"rejected"}'
    Path("result.json").write_bytes(output)


def main() -> int:
    try:
        apply_resource_limits()
    except ResourceLimitUnavailable:
        _reply({"ok": False, "error": "resource_limits"})
        return 0
    try:
        # Import only after the process boundary exists. Parser imports can load
        # optional binary libraries and must never happen before OS admission.
        with Path("request.json").open("rb") as stream:
            request_bytes = stream.read(2_049)
        if len(request_bytes) > 2_048:
            raise ValueError("Invalid worker request")
        request = json.loads(request_bytes)
        if not isinstance(request, dict):
            raise ValueError("Invalid worker request")
        filename = request.get("filename")
        if not isinstance(filename, str):
            raise ValueError("Invalid worker request")
        with Path("input.bin").open("rb") as stream:
            data = stream.read(MAX_INPUT_BYTES + 1)
        if request.get("mode") == "document" and set(request) == {"mode", "filename"}:
            from ase.adapters.research_imports import extract_upload  # noqa: PLC0415

            result = extract_upload(data, filename)
            _reply({"ok": True, "result": asdict(result)})
        elif request.get("mode") == "media" and set(request) == {"mode", "filename", "tools"}:
            from ase.adapters.research_media import MediaTools, extract_media  # noqa: PLC0415
            from ase.adapters.research_media.worker_protocol import (  # noqa: PLC0415
                encode_media_result,
            )

            tools = request["tools"]
            if not isinstance(tools, dict) or set(tools) != {"tesseract", "ffmpeg", "ffprobe"}:
                raise ValueError("Invalid worker configuration")
            if any(value is not None and not isinstance(value, str) for value in tools.values()):
                raise ValueError("Invalid worker configuration")
            media = extract_media(data, filename, MediaTools(**tools))
            _reply(encode_media_result(media), MAX_MEDIA_OUTPUT_BYTES)
        else:
            raise ValueError("Invalid worker mode")
    except Exception:
        # No parser excerpts, filenames, paths, stack traces or raw input escape
        # through error channels. The parent receives a fixed failure category.
        _reply({"ok": False, "error": "rejected"})
    return 0


if __name__ == "__main__":
    sys.exit(main())
