"""Operator-run downloads of large public files with an explicit byte ceiling."""

from __future__ import annotations

from pathlib import Path

import httpx

DEFAULT_CONTACT = "https://github.com/ShabalalaWATP/OSINT"
CHUNK = 256 * 1024


def user_agent(contact: str) -> str:
    return f"TheAllSeeingEye/0.1 ({contact}) importer"


def download_to(client: httpx.Client, url: str, destination: Path, max_bytes: int) -> int:
    """Stream one HTTPS file to disk, stopping as soon as the ceiling is crossed."""
    if not url.startswith("https://"):
        raise ValueError("Importer downloads must use https")
    received = 0
    with client.stream("GET", url, follow_redirects=True) as response:
        response.raise_for_status()
        declared = response.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > max_bytes:
            raise ValueError(f"{url} declares more than {max_bytes} bytes")
        with destination.open("wb") as handle:
            for chunk in response.iter_bytes(CHUNK):
                received += len(chunk)
                if received > max_bytes:
                    raise ValueError(f"{url} exceeded {max_bytes} bytes")
                handle.write(chunk)
    return received
