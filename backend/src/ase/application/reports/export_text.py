"""Plain-text Markdown boundaries, safe link destinations and shared review wording."""

from __future__ import annotations

import re
from html import escape
from ipaddress import IPv6Address
from urllib.parse import quote, unquote, urlsplit, urlunsplit

from ase.domain.reports import ReportStatus

_MARKUP = re.compile(r"([\\`*_{}\[\]|#!~@])")


def plain_markdown(text: str) -> str:
    """Render untrusted content inline, without HTML, blocks, images or autolinks."""
    value = " ".join(text.split())
    value = _MARKUP.sub(r"\\\1", escape(value, quote=False))
    value = re.sub(r"^(\d{1,9})([.)])(?=\s)", r"\1\\\2", value)
    value = re.sub(r"^([-+=])(?=\s|$)", r"\\\1", value)
    value = re.sub(r"(?i)\bwww\.", r"www\\.", value)
    return re.sub(r"(?i)\b(https?)://", lambda match: match[1] + "\\://", value)


def safe_url(value: str | None) -> str | None:
    """Accept explicit HTTP(S) links only, encoding Markdown destination delimiters."""
    if not value or len(value) > 4096:
        return None
    if any(ord(c) <= 32 or ord(c) == 127 or c in '\\<>"`' for c in value):
        return None
    if any(ord(c) < 32 or ord(c) == 127 for c in unquote(value)):
        return None
    try:
        parts = urlsplit(value)
        if (
            parts.scheme.lower() not in {"http", "https"}
            or not parts.hostname
            or parts.username is not None
            or parts.password is not None
        ):
            return None
        host = parts.hostname.encode("idna").decode("ascii")
        if ":" in host:
            host = f"[{IPv6Address(host)}]"
        elif not re.fullmatch(r"[A-Za-z0-9.-]+", host):
            raise ValueError("Invalid link host")
        netloc = host + (f":{parts.port}" if parts.port is not None else "")
    except (ValueError, UnicodeError):
        return None
    return urlunsplit(
        (
            parts.scheme.lower(),
            netloc,
            quote(parts.path, safe="/%:@-._~!$&*+,;="),
            quote(parts.query, safe="/%?:@-._~!$&*+,;="),
            quote(parts.fragment, safe="/%?:@-._~!$&*+,;="),
        )
    )


def review_notice(status: ReportStatus | None) -> str:
    if status is ReportStatus.FAILED:
        return (
            "FAILED GENERATION: this version is not an assessment; "
            "automated checks did not complete."
        )
    if status is ReportStatus.NEEDS_REVIEW:
        return "NEEDS REVIEW: this version did not pass all required automated checks."
    if status is ReportStatus.READY:
        return (
            "READY: required automated checks passed. Analyst verification has not been recorded."
        )
    return (
        "Review status was not recorded here. "
        "Passing automated checks does not establish analyst verification."
    )
