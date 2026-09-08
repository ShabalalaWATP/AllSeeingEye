"""Plain-text Markdown boundaries and shared frozen-evidence presentation."""

from __future__ import annotations

import re
from dataclasses import fields, is_dataclass, replace
from datetime import UTC, datetime
from html import escape
from ipaddress import IPv6Address
from typing import Any, cast
from urllib.parse import quote, unquote, urlsplit, urlunsplit

from ase.application.reports.observation_text import observation_lines
from ase.application.reports.source_provenance_text import source_provenance_lines
from ase.domain.evidence import EvidenceItem
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


def markdown_fields[T](value: T) -> T:
    """Escape free text recursively in the report's immutable content dataclasses.

    Enums and datetimes remain their original types. URLs in evidence are handled
    separately by ``safe_url``; evidence must not be passed through this projection.
    """
    if type(value) is str:
        return cast(T, plain_markdown(cast(str, value)))
    if isinstance(value, tuple):
        return cast(T, tuple(markdown_fields(item) for item in value))
    if is_dataclass(value) and not isinstance(value, type):
        changes: dict[str, Any] = {
            f.name: markdown_fields(getattr(value, f.name)) for f in fields(value)
        }
        return replace(value, **changes)
    return value


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


def timestamp(value: datetime | None) -> str:
    if value is None:
        return "unknown"
    if value.tzinfo is None:
        return value.isoformat() + " (timezone unknown)"
    return value.astimezone(UTC).isoformat()


def evidence_metadata(item: EvidenceItem) -> tuple[str, ...]:
    coordinates = "unknown" if item.lon is None or item.lat is None else f"{item.lon}, {item.lat}"
    return (
        f"Published: {timestamp(item.published_at)}",
        f"Observed: {timestamp(item.observed_at)}",
        f"Captured: {timestamp(item.captured_at)}",
        f"Language: {item.language or 'unknown'}",
        f"Source ID: {item.source_id}",
        f"Declared organisation: {item.independence_key or 'unknown'}; "
        "independent sourcing not verified",
        f"Reliability: {item.reliability}; credibility: {item.credibility}",
        f"Grade rationale: {item.grade_rationale or 'Not provided.'}",
        f"Category: {item.category}; country: {item.country_iso or 'unknown'}",
        f"Location precision: {item.geo_confidence or 'unknown'}; "
        f"coordinates (longitude, latitude): {coordinates}",
        f"Instrument: {'yes' if item.instrument else 'no'}",
        f"Topic cluster: {item.story_id or 'unknown'}; grouping is not corroboration",
        f"Event ID: {item.event_id}",
        f"Content hash: {item.content_hash or 'unknown'}",
        *observation_lines(item),
        *source_provenance_lines(item),
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
