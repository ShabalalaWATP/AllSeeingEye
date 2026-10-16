"""Validate the generated contact response, or warn about the reviewed image expiry."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
from pathlib import Path

from check_web_image import fetch

ROOT = Path(__file__).resolve().parents[1]
EXPIRY = ROOT / "infra/caddy-build/security-contact/expiry.txt"
POLICY = "https://github.com/ShabalalaWATP/AllSeeingEye/security/policy"


def expiry_warning(expires: str, now: datetime) -> str | None:
    end = datetime.fromisoformat(expires)
    if end.tzinfo is None or end > now + timedelta(days=366):
        raise ValueError("Invalid reviewed security contact expiry")
    if end <= now + timedelta(days=30):
        return "Review security contact and renew infra/caddy-build/security-contact/expiry.txt"
    return None


def problems(
    base: str, contact: str | None, canonical: str | None, policy: str = POLICY
) -> list[str]:
    status, headers, body = fetch(base, "/.well-known/security.txt")
    found = []
    expected_status = 200 if contact else 404
    if status != expected_status:
        found.append(f"security.txt answered {status}, expected {expected_status}")
    for name in (
        "Content-Security-Policy",
        "Strict-Transport-Security",
        "Permissions-Policy",
        "Referrer-Policy",
        "X-Frame-Options",
        "X-Content-Type-Options",
    ):
        if not headers.get(name):
            found.append(f"security.txt lacks {name}")
    if headers.get("Content-Type", "").lower() != "text/plain; charset=utf-8":
        found.append("security.txt lacks the explicit UTF-8 plain-text type")
    if not contact:
        return found
    text = body.decode("utf-8", errors="strict")
    fields: dict[str, list[str]] = {}
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition(":")
        if not separator:
            found.append("security.txt contains a malformed field")
        fields.setdefault(key.lower(), []).append(value.strip())
    for key, expected in (
        ("contact", contact),
        ("canonical", canonical),
        ("preferred-languages", "en"),
        ("policy", policy),
    ):
        if fields.get(key) != [expected]:
            found.append(f"security.txt has an unexpected {key}")
    expiry = fields.get("expires", [])
    try:
        if len(expiry) != 1 or datetime.fromisoformat(expiry[0]) <= datetime.now(UTC):
            raise ValueError("missing or expired")
        expiry_warning(expiry[0], datetime.now(UTC))
    except (ValueError, TypeError):
        found.append("security.txt has missing, invalid or expired Expires")
    if not text.endswith("\n") or "<html" in text.lower():
        found.append("security.txt is not a terminated plain-text document")
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base", nargs="?")
    parser.add_argument("--contact")
    parser.add_argument("--canonical")
    parser.add_argument("--policy", default=POLICY)
    args = parser.parse_args()
    if args.base:
        failures = problems(
            args.base.rstrip("/"), args.contact, args.canonical, args.policy
        )
        for failure in failures:
            print(failure)
        return int(bool(failures))
    warning = expiry_warning(
        EXPIRY.read_text(encoding="utf-8").strip(), datetime.now(UTC)
    )
    if warning:
        print(f"::warning title=Security contact expiry::{warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
