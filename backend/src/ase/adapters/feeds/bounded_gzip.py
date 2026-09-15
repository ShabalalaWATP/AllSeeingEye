"""Bounded gzip compatibility for unauthenticated feeds that ignore Accept-Encoding.

Feed requests advertise identity only, but some publishers (the UN RSS endpoints on
10 September 2026, The Independent on 15 September 2026) answer gzip regardless.
Those responses are decoded from raw HTTP bytes with independent wire and expanded
caps, so HTTPX cannot decompress before the size check. Credentialed requests stay
identity-only, and every other encoding is still refused before the body is read.
"""

import zlib
from collections.abc import Awaitable, Callable

import httpx


class BoundedGzipError(Exception):
    """Safe transport failure without provider content or request identifiers."""


async def read_feed_response(
    response: httpx.Response,
    max_bytes: int,
    *,
    credentialed: bool,
    default_reader: Callable[[httpx.Response], Awaitable[bytes]],
) -> bytes:
    """Decode a single gzip member for unauthenticated requests; otherwise the default path."""
    if not credentialed and response.headers.get("content-encoding", "").strip().lower() == "gzip":
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
