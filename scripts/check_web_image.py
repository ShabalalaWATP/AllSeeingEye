"""Smoke-test static serving by a running web image (CI runs it after the image build).

Usage: python scripts/check_web_image.py http://localhost:8080

Checks what only the real Caddy build can show: the security policy is sent,
pre-compressed files are served, content-hashed assets are immutable, the shell and
fixed-name files revalidate, and a missing asset answers 404 rather than the shell.
"""

from __future__ import annotations

import re
import sys
import urllib.error
import urllib.request
from email.message import Message

MISSING_ASSET = "/assets/index-Missing0.js"


def fetch(
    base: str, path: str, encoding: str = "identity"
) -> tuple[int, Message, bytes]:
    request = urllib.request.Request(base + path, headers={"Accept-Encoding": encoding})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, response.headers, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.headers, b""


def problems(base: str) -> list[str]:
    found: list[str] = []

    def expect(condition: bool, message: str) -> None:
        if not condition:
            found.append(message)

    status, headers, body = fetch(base, "/")
    expect(status == 200, f"/ answered {status}")
    expect(
        "default-src 'self'" in headers.get("Content-Security-Policy", ""),
        "no CSP on /",
    )
    expect(headers.get("Cache-Control") == "no-cache", "the shell is not revalidated")
    entry = re.search(rb'src="(/assets/index-[^"]+\.js)"', body)
    expect(entry is not None, "the shell names no entry script")

    status, headers, _ = fetch(base, "/research/saved")
    expect(status == 200, f"a client route answered {status}")

    if entry is not None:
        asset = entry.group(1).decode()
        status, headers, _ = fetch(base, asset, "br")
        expect(status == 200, f"{asset} answered {status}")
        expect(
            headers.get("Content-Encoding") == "br", "no pre-compressed Brotli asset"
        )
        expect(
            "immutable" in headers.get("Cache-Control", ""),
            "hashed asset not immutable",
        )

    status, headers, _ = fetch(base, "/assets/maplibre-gl-worker.mjs")
    expect(status == 200, f"the MapLibre worker answered {status}")
    expect(
        headers.get("Cache-Control") == "no-cache",
        "fixed-name asset is not revalidated",
    )

    status, headers, _ = fetch(base, MISSING_ASSET)
    expect(status == 404, f"a missing asset answered {status}, not 404")
    expect(
        "immutable" not in headers.get("Cache-Control", ""),
        "a 404 was cached as immutable",
    )
    return found


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: check_web_image.py BASE_URL")
    failures = problems(sys.argv[1].rstrip("/"))
    for failure in failures:
        print(f"check_web_image: {failure}", file=sys.stderr)
    print(
        "Web image checks passed."
        if not failures
        else f"{len(failures)} check(s) failed."
    )
    sys.exit(1 if failures else 0)
