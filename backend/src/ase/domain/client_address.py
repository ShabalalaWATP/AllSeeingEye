"""Client address keys for abuse limits.

A single IPv6 subscriber usually controls a whole /64, so keying limits on the full
address would hand one client billions of separate buckets. IPv6 clients therefore
share a bucket per /64 prefix, IPv4-mapped IPv6 addresses count as their IPv4 address
and IPv4 is unchanged. Audit records keep the full address; only limit keys use this.
"""

from __future__ import annotations

from ipaddress import IPv4Address, IPv6Address, IPv6Network, ip_address

IPV6_PREFIX_LENGTH = 64
UNKNOWN_CLIENT = "unknown"
_MAX_RAW_KEY = 64


def rate_limit_key(ip: str | None) -> str:
    """Return the bucket name for a client address, normalising IPv6 to its /64."""
    if not ip:
        return UNKNOWN_CLIENT
    try:
        address = ip_address(ip)
    except ValueError:
        # Not an address (for example a Unix socket peer). Bound it rather than trust it.
        return ip[:_MAX_RAW_KEY]
    if isinstance(address, IPv4Address):
        return str(address)
    return _ipv6_key(address)


def _ipv6_key(address: IPv6Address) -> str:
    mapped = address.ipv4_mapped
    if mapped is not None:
        return str(mapped)
    host_bits = 128 - IPV6_PREFIX_LENGTH
    prefix = (int(address) >> host_bits) << host_bits
    return str(IPv6Network((prefix, IPV6_PREFIX_LENGTH)))
