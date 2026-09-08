"""Optional isolated renderer configuration, loaded only from an operator-owned file."""

import json
from pathlib import Path

from ase.adapters.reports.async_documents import AsyncReportDocumentRenderer
from ase.adapters.reports.chromium import ChromiumPdfWorker
from ase.adapters.reports.chromium_runtime import LinuxChromiumPolicy, immutable_path
from ase.domain.errors import InvalidRequest


def build_report_renderer(path: str | None) -> AsyncReportDocumentRenderer:
    if path is None:
        return AsyncReportDocumentRenderer()
    try:
        location = Path(path)
        if not location.is_absolute() or location.is_symlink():
            raise ValueError("Invalid runtime configuration")
        immutable_path(location)
        with location.open("rb") as stream:
            raw = stream.read(16_385)
        if len(raw) > 16_384:
            raise ValueError("Oversized runtime configuration")
        data = json.loads(raw)
        if (
            not isinstance(data, dict)
            or set(data)
            != {
                "rootfs",
                "browser",
                "browser_sha256",
                "bubblewrap",
                "bubblewrap_sha256",
                "cgroup_root",
            }
            or any(not isinstance(v, str) for v in data.values())
        ):
            raise ValueError("Invalid runtime configuration")
        policy = LinuxChromiumPolicy(
            Path(data["rootfs"]),
            data["browser"],
            data["browser_sha256"],
            Path(data["bubblewrap"]),
            data["bubblewrap_sha256"],
            Path(data["cgroup_root"]),
        )
        return AsyncReportDocumentRenderer(worker=ChromiumPdfWorker(policy))
    except (OSError, ValueError, TypeError):
        raise InvalidRequest("The configured isolated PDF runtime is invalid.") from None
