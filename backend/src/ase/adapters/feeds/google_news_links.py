"""Resolve the older Google News envelope without collecting HTML.

Modern opaque AU_yqL IDs require batchexecute parameters extracted from an HTML article
page by current decoder libraries. That workflow violates this project's feeds/APIs-only
rule. Those links remain unchanged until a supported API can supply the parameters.
"""

from __future__ import annotations

import base64
import binascii
import re
from urllib.parse import urlsplit

from ase.adapters.feeds.http import FeedFetchError, assert_public_host

MAX_URL_LENGTH = 2_048
_ARTICLE = re.compile(r"^/(?:rss/)?(?:articles|read)/([A-Za-z0-9_-]+)$")
_PREFIX = b'\x08\x13"'


def _acceptable_url(url: str) -> bool:
    if not url or len(url) > MAX_URL_LENGTH or any(char.isspace() for char in url):
        return False
    if any(ord(char) < 32 or ord(char) == 127 for char in url) or chr(92) in url:
        return False
    try:
        parts = urlsplit(url)
        return (
            parts.scheme in ("http", "https")
            and bool(parts.hostname)
            and parts.username is None
            and parts.password is None
            and parts.port in (None, 80, 443)
        )
    except ValueError:
        return False


def _unpack_url(token: str) -> str | None:
    try:
        data = base64.b64decode(token + "=" * (-len(token) % 4), altchars=b"-_", validate=True)
        if not data.startswith(_PREFIX):
            return None
        offset, length = len(_PREFIX), 0
        for shift in range(0, 35, 7):
            byte = data[offset]
            offset += 1
            length |= (byte & 0x7F) << shift
            if byte < 0x80:
                break
        else:
            return None
        if not 0 < length <= MAX_URL_LENGTH or offset + length > len(data):
            return None
        target = data[offset : offset + length].decode("utf-8")
    except (binascii.Error, IndexError, UnicodeError):
        return None
    return target if _acceptable_url(target) else None


def decode_embedded_url(url: str) -> str | None:
    """Decode a length-delimited URL, refusing opaque IDs and malformed envelopes."""
    if not _acceptable_url(url):
        return None
    parts = urlsplit(url)
    if parts.hostname != "news.google.com" or parts.scheme != "https":
        return None
    match = _ARTICLE.fullmatch(parts.path)
    return _unpack_url(match.group(1)) if match else None


class GoogleNewsUrlResolver:
    async def resolve(self, url: str) -> str | None:
        target = decode_embedded_url(url)
        if target is None:
            return None
        try:
            await assert_public_host(target)
        except (FeedFetchError, ValueError):
            return None
        return target
