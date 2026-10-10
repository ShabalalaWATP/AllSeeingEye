"""Smoke-test static serving by a running web image (CI runs it after the image build).

Usage: python scripts/check_web_image.py http://localhost:8080

Checks what only the real Caddy build can show: the security policy is sent,
pre-compressed files are served, content-hashed assets (the MapLibre worker included)
are immutable, the shell revalidates, no fixed-name MapLibre worker is served, a
missing asset answers 404 rather than the shell, and robots.txt and security.txt are
served as text while any other /.well-known path answers 404.
"""

from __future__ import annotations

import re
import sys
import urllib.error
import urllib.request
from email.message import Message

MISSING_ASSET = "/assets/index-Missing0.js"
# Static, dynamic and URL references between built chunks, all within /assets.
CHUNK_REFERENCE = re.compile(rb"[\"'`](?:\./|/assets/)([\w-]+\.js)[\"'`]")
WORKER_CHUNK = re.compile(r"maplibre-gl-worker-[\w-]{8}\.js$")


def fetch(
    base: str, path: str, encoding: str = "identity"
) -> tuple[int, Message, bytes]:
    request = urllib.request.Request(base + path, headers={"Accept-Encoding": encoding})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, response.headers, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.headers, b""


def maplibre_worker(base: str, entry: str, limit: int = 400) -> str | None:
    """Follows chunk references from the entry to the hashed worker the map starts."""
    pending, seen = [entry], set()
    while pending and len(seen) < limit:
        chunk = pending.pop()
        if chunk in seen:
            continue
        seen.add(chunk)
        status, _, body = fetch(base, chunk)
        if status != 200:
            continue
        for match in CHUNK_REFERENCE.finditer(body):
            name = match.group(1).decode()
            if WORKER_CHUNK.match(name):
                return f"/assets/{name}"
            pending.append(f"/assets/{name}")
    return None


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
    expect(
        not headers.get("Link"), "the ordinary shell preloads public product content"
    )
    entry = re.search(rb'src="(/assets/index-[^"]+\.js)"', body)
    expect(entry is not None, "the shell names no entry script")

    for product_path in ("/enterprise", "/enterprise/", "/ENTERPRISE"):
        status, product_headers, product_body = fetch(base, product_path)
        expect(status == 200, f"{product_path} answered {status}")
        expect(product_body == body, f"{product_path} changed the gated SPA shell")
        expect(
            product_headers.get("Link")
            == "</brand/eye-512.webp>; rel=preload; as=image; type=image/webp; fetchpriority=high",
            f"{product_path} did not preload the existing hero capture",
        )
        expect(
            product_headers.get("Content-Security-Policy")
            == headers.get("Content-Security-Policy"),
            f"{product_path} changed the shared security policy",
        )

    status, headers, _ = fetch(base, "/research/saved")
    expect(status == 200, f"a client route answered {status}")
    expect(not headers.get("Link"), "an application route preloads the product hero")

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

    worker = maplibre_worker(base, entry.group(1).decode()) if entry else None
    expect(worker is not None, "no hashed MapLibre worker chunk is reachable")
    if worker is not None:
        status, headers, _ = fetch(base, worker)
        expect(status == 200, f"the MapLibre worker answered {status}")
        expect(
            "immutable" in headers.get("Cache-Control", ""),
            "the hashed MapLibre worker is not immutable",
        )
    status, _, _ = fetch(base, "/assets/maplibre-gl-worker.mjs")
    expect(status == 404, f"a fixed-name MapLibre worker answered {status}")

    status, headers, _ = fetch(base, MISSING_ASSET)
    expect(status == 404, f"a missing asset answered {status}, not 404")
    expect(
        "immutable" not in headers.get("Cache-Control", ""),
        "a 404 was cached as immutable",
    )
    found.extend(well_known_problems(base))
    return found


def well_known_problems(base: str) -> list[str]:
    """robots.txt and security.txt are real text files; other /.well-known paths 404."""
    found = []
    for path, marker in (
        ("/robots.txt", b"Disallow: /api/"),
        ("/.well-known/security.txt", b"Contact: "),
    ):
        status, headers, body = fetch(base, path)
        if status != 200 or marker not in body:
            found.append(f"{path} answered {status} without its expected content")
        if not headers.get("Content-Type", "").startswith("text/plain"):
            found.append(f"{path} is not served as text/plain")
    status, _, _ = fetch(base, "/.well-known/missing-probe")
    if status != 404:
        found.append(f"an unknown /.well-known path answered {status}, not 404")
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
