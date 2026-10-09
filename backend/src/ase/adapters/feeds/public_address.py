"""Public-address admission and URL pinning shared by outbound adapters."""

import asyncio
import ipaddress
import socket
from urllib.parse import urlsplit, urlunsplit

from ase.adapters.feeds.http_contracts import FeedFetchError

_TRANSLATION_PREFIXES = (
    ipaddress.IPv6Network("64:ff9b::/96"),
    ipaddress.IPv6Network("64:ff9b:1::/48"),
)


def is_public_address(host: str) -> bool:
    """Only globally routable addresses; shared CGNAT space (100.64.0.0/10) is not global."""
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return True  # a hostname; resolved and checked separately
    if isinstance(address, ipaddress.IPv6Address) and (
        address.ipv4_mapped is not None
        or address.sixtofour is not None
        or address.teredo is not None
        or any(address in prefix for prefix in _TRANSLATION_PREFIXES)
    ):
        return False
    return bool(
        address.is_global
        and not (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_multicast
            or address.is_reserved
            or address.is_unspecified
        )
    )


async def assert_public_host(url: str) -> str | None:
    """Refuse URLs whose host resolves to private space; return the address to connect to.

    Returns None for a literal public IP address (nothing to pin) and raises on any
    private, loopback or link-local answer. Callers must connect to the returned address
    rather than resolving again, which is what closes the DNS rebinding window.
    """
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise FeedFetchError(f"Unsupported URL: {url}")
    if parts.username or parts.password:
        raise FeedFetchError("Credentials in feed URLs are not allowed")
    host = parts.hostname
    if not is_public_address(host):
        raise FeedFetchError(f"Refusing to fetch a non-public address: {host}")
    try:
        ipaddress.ip_address(host)
        return None
    except ValueError:
        pass
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise FeedFetchError(f"Cannot resolve {host}") from exc
    addresses = [str(info[4][0]) for info in infos]
    for address in addresses:
        if not is_public_address(address):
            raise FeedFetchError(f"Refusing to fetch {host}: resolves to a non-public address")
    if not addresses:
        raise FeedFetchError(f"Cannot resolve {host}")
    return addresses[0]


def pin_url(url: str, address: str) -> str:
    """The same URL with the host replaced by the address that was checked."""
    parts = urlsplit(url)
    literal = f"[{address}]" if ":" in address else address
    netloc = literal if parts.port is None else f"{literal}:{parts.port}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
