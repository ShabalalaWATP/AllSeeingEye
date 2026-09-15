"""Restrictive E02 policy and the metadata a guarded transport adapter must supply.

No transport is implemented here. A future binding must use the public-source DNS pinning
guard for every hop, honour these limits while streaming, and never follow redirects itself
without a fresh guard check. Source rate/cooldown admission is also required before each
dispatch. A byte-only or administrator LLM client is not this contract.
"""

import ipaddress
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal
from urllib.parse import parse_qsl, urljoin, urlsplit

POLICY_VERSION = "ase-original-acquisition-v1"
MAX_ORIGINAL_BYTES = 2 * 1024 * 1024
MAX_REDIRECTS = 2
MAX_ACQUISITION_SECONDS = 20.0
MAX_RETENTION_DAYS = 30
_TRANSLATION_PREFIXES = (
    ipaddress.IPv6Network("64:ff9b::/96"),
    ipaddress.IPv6Network("64:ff9b:1::/48"),
)
MEDIA_EXTENSIONS = {
    "text/plain": ".txt",
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}
SAFE_FETCH_REASONS = frozenset(
    {
        "request_not_permitted",
        "destination_not_permitted",
        "source_admission_failed",
        "source_rate_or_terms_not_permitted",
        "redirect_limit",
        "http_status_not_permitted",
        "compressed_response_not_permitted",
        "body_limit_or_size_mismatch",
        "unsupported_media_type",
        "transport_receipt_invalid",
        "transport_failed",
        "fetch_timeout",
    }
)


class OriginalFetchRejected(Exception):
    """A bounded, display-safe reason; never include a URL or response body."""

    def __init__(self, reason: str) -> None:
        if reason not in SAFE_FETCH_REASONS:
            raise ValueError("Unknown original transport failure")
        self.reason = reason
        super().__init__(reason)


def public_address(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    return bool(
        address.is_global
        and not address.is_multicast
        and not address.is_reserved
        and not (
            isinstance(address, ipaddress.IPv6Address)
            and (
                address.ipv4_mapped
                or address.sixtofour
                or address.teredo
                or any(address in prefix for prefix in _TRANSLATION_PREFIXES)
            )
        )
    )


def public_origin(url: str) -> str:
    """Static rejection only; DNS resolution and connection pinning remain mandatory."""
    if (
        not isinstance(url, str)
        or not 1 <= len(url) <= 2048
        or any(ord(char) < 33 or ord(char) > 126 for char in url)
        or "\\" in url
    ):
        raise ValueError("Original URL is not permitted")
    try:
        parts = urlsplit(url)
        host = parts.hostname or ""
        if (
            parts.scheme != "https"
            or not host
            or parts.username is not None
            or parts.password is not None
            or parts.fragment
            or parts.port not in (None, 443)
        ):
            raise ValueError("Original URL is not permitted")
        try:
            ipaddress.ip_address(host)
        except ValueError:
            if (
                "." not in host
                or host.endswith((".local", ".localhost", ".internal", ".test"))
                or not re.fullmatch(r"[a-zA-Z0-9.-]+", host)
                or ".." in host
            ):
                raise ValueError("Original URL is not permitted") from None
        else:
            if not public_address(host):
                raise ValueError("Original URL is not permitted")
    except ValueError:
        raise ValueError("Original URL is not permitted") from None
    return f"https://[{host}]" if ":" in host else f"https://{host.lower()}"


@dataclass(frozen=True, slots=True)
class OriginalSourcePolicy:
    source_id: str
    policy_id: str
    allowed_origins: tuple[str, ...]
    reviewed_at: datetime
    valid_until: datetime
    terms: Literal["allowed", "denied", "unknown"] = "unknown"
    robots: Literal["allowed", "denied", "unknown", "not_applicable"] = "unknown"
    permitted_use: str = ""
    allowed_query_keys: tuple[str, ...] = ()
    allowed_path_prefixes: tuple[str, ...] = ("/",)
    retention_days: int = 1
    max_bytes: int = MAX_ORIGINAL_BYTES
    max_redirects: int = MAX_REDIRECTS
    timeout_seconds: float = MAX_ACQUISITION_SECONDS

    def __post_init__(self) -> None:
        if (
            not 1 <= len(self.source_id) <= 100
            or not 1 <= len(self.policy_id) <= 100
            or type(self.allowed_origins) is not tuple
            or not self.allowed_origins
            or len(self.allowed_origins) > 8
            or any(public_origin(origin) != origin for origin in self.allowed_origins)
            or self.reviewed_at.utcoffset() is None
            or self.valid_until.utcoffset() is None
            or not self.reviewed_at < self.valid_until <= self.reviewed_at + timedelta(days=7)
            or type(self.retention_days) is not int
            or not 1 <= self.retention_days <= MAX_RETENTION_DAYS
            or type(self.max_bytes) is not int
            or not 1 <= self.max_bytes <= MAX_ORIGINAL_BYTES
            or type(self.max_redirects) is not int
            or not 0 <= self.max_redirects <= MAX_REDIRECTS
            or not 0 < self.timeout_seconds <= MAX_ACQUISITION_SECONDS
            or type(self.allowed_query_keys) is not tuple
            or len(self.allowed_query_keys) > 20
            or any(
                not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", key) for key in self.allowed_query_keys
            )
            or type(self.allowed_path_prefixes) is not tuple
            or not 1 <= len(self.allowed_path_prefixes) <= 16
            or any(
                not value.startswith("/") or not value.endswith("/")
                for value in self.allowed_path_prefixes
            )
        ):
            raise ValueError("Invalid original acquisition policy")

    def permits(self, url: str, now: datetime) -> bool:
        if (
            now.utcoffset() is None
            or self.terms != "allowed"
            or self.robots not in ("allowed", "not_applicable")
            or not self.permitted_use.strip()
            or len(self.permitted_use) > 1000
            or not self.reviewed_at <= now < self.valid_until
        ):
            return False
        try:
            origin = public_origin(url)
            parts = urlsplit(url)
            query = parse_qsl(parts.query, strict_parsing=True, max_num_fields=20)
            # Encoded separators or dot segments must not escape a reviewed robots/path scope.
            if "%" in parts.path or any(part in (".", "..") for part in parts.path.split("/")):
                return False
            return (
                origin in self.allowed_origins
                and any(
                    (parts.path or "/").startswith(prefix) for prefix in self.allowed_path_prefixes
                )
                and all(key in self.allowed_query_keys for key, _ in query)
            )
        except (ValueError, TypeError):
            return False


@dataclass(frozen=True, slots=True)
class OriginalFetchRequest:
    url: str = field(repr=False)
    policy: OriginalSourcePolicy
    max_bytes: int
    max_redirects: int
    timeout_seconds: float
    accept: tuple[str, ...] = tuple(MEDIA_EXTENSIONS)
    accept_encoding: Literal["identity"] = "identity"


@dataclass(frozen=True, slots=True)
class OriginalTransportHop:
    url: str = field(repr=False)
    resolved_addresses: tuple[str, ...]
    connected_address: str
    status_code: int
    redirect_location: str | None = field(default=None, repr=False)


@dataclass(frozen=True, slots=True)
class OriginalFetchResponse:
    requested_url: str = field(repr=False)
    canonical_url: str = field(repr=False)
    hops: tuple[OriginalTransportHop, ...]
    media_type: str
    body: bytes = field(repr=False)
    wire_body_bytes: int
    content_encoding: str = "identity"
    last_modified_at: datetime | None = None
    etag: str | None = None


def validate_response(  # noqa: PLR0911 - explicit trust-boundary failures produce distinct receipts
    result: OriginalFetchResponse,
    request: OriginalFetchRequest,
    policy: OriginalSourcePolicy,
    now: datetime,
) -> str | None:
    """Reject incomplete or inconsistent guard evidence; never infer missing safety checks."""
    if (
        result.requested_url != request.url
        or not result.hops
        or len(result.hops) > request.max_redirects + 1
        or result.hops[0].url != request.url
        or result.hops[-1].url != result.canonical_url
    ):
        return "transport_receipt_invalid"
    for index, hop in enumerate(result.hops):
        if (
            not policy.permits(hop.url, now)
            or not hop.resolved_addresses
            or len(hop.resolved_addresses) > 32
            or any(not public_address(address) for address in hop.resolved_addresses)
            or hop.connected_address not in hop.resolved_addresses
        ):
            return "destination_not_permitted"
        expected = {200} if index == len(result.hops) - 1 else {301, 302, 303, 307, 308}
        if hop.status_code not in expected:
            return "http_status_not_permitted"
        if index < len(result.hops) - 1:
            location = hop.redirect_location
            if (
                not isinstance(location, str)
                or not 1 <= len(location) <= 2048
                or any(ord(char) < 33 or ord(char) > 126 for char in location)
                or urljoin(hop.url, location) != result.hops[index + 1].url
            ):
                return "transport_receipt_invalid"
    if result.content_encoding not in ("", "identity"):
        return "compressed_response_not_permitted"
    if (
        not result.body
        or len(result.body) > request.max_bytes
        or result.wire_body_bytes != len(result.body)
    ):
        return "body_limit_or_size_mismatch"
    if result.media_type not in request.accept:
        return "unsupported_media_type"
    if result.last_modified_at is not None and result.last_modified_at.utcoffset() is None:
        return "transport_receipt_invalid"
    if result.etag is not None and (
        len(result.etag) > 200 or any(ord(char) < 32 for char in result.etag)
    ):
        return "transport_receipt_invalid"
    return None
