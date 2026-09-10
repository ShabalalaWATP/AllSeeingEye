"""Narrow gzip compatibility for verified public UN feeds, with independent caps.

Both exact URLs returned gzip despite Accept-Encoding: identity on 10 September
2026. This exception does not cover redirects, credentials or other feed URLs.
Read raw HTTP bytes so HTTPX cannot decompress before the expanded-size check.
"""

import zlib
from collections.abc import Awaitable, Callable

import httpx

GZIP_RSS_URLS = frozenset(
    {
        "https://news.un.org/feed/subscribe/en/news/all/rss.xml",
        "https://press.un.org/en/rss.xml",
    }
)


class BoundedGzipError(Exception):
    """Safe transport failure without provider content or request identifiers."""


async def read_feed_response(
    response: httpx.Response,
    max_bytes: int,
    initial_url: str,
    final_url: str,
    *,
    credentialed: bool,
    redirected: bool,
    default_reader: Callable[[httpx.Response], Awaitable[bytes]],
) -> bytes:
    """Keep normal transport policy unless the exact unauthenticated UN seed matches."""
    if (
        not credentialed
        and not redirected
        and initial_url == final_url
        and initial_url in GZIP_RSS_URLS
        and response.headers.get("content-encoding", "").strip().lower() == "gzip"
    ):
        return await read_bounded_gzip(response, max_bytes)
    return await default_reader(response)


async def read_bounded_gzip(response: httpx.Response, max_bytes: int) -> bytes:
    """Decode one gzip member, limiting both the wire bytes and expanded output."""
    declared = response.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > max_bytes:
        raise BoundedGzipError("Feed compressed response exceeds byte limit")
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
    encoded_size, decoded_size = 0, 0
    chunks: list[bytes] = []
    try:
        async for chunk in response.aiter_raw():
            encoded_size += len(chunk)
            if encoded_size > max_bytes:
                raise BoundedGzipError("Feed compressed response exceeds byte limit")
            decoded = decoder.decompress(chunk, max_bytes - decoded_size + 1)
            decoded_size += len(decoded)
            if decoded_size > max_bytes:
                raise BoundedGzipError("Feed decoded response exceeds byte limit")
            if decoder.unused_data:
                raise BoundedGzipError("Invalid or trailing feed gzip stream")
            chunks.append(decoded)
        if not decoder.eof or decoder.unconsumed_tail:
            raise BoundedGzipError("Incomplete feed gzip stream")
    except zlib.error:
        raise BoundedGzipError("Invalid feed gzip stream") from None
    return b"".join(chunks)
