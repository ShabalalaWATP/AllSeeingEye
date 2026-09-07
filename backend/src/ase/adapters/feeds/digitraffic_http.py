"""Digitraffic requires gzip and application identification without personal data."""

import zlib
from typing import Any

import httpx

from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient


class DigitrafficHttpClient(FeedHttpClient):
    @staticmethod
    def _pinned(
        url: str, address: str | None, headers: dict[str, str]
    ) -> tuple[str, dict[str, Any]]:
        headers.update(
            {
                "Accept-Encoding": "gzip",
                "User-Agent": "TheAllSeeingEye/0.1",
                "Digitraffic-User": "TheAllSeeingEye/0.1",
            }
        )
        return FeedHttpClient._pinned(url, address, headers)

    async def _read_bounded(self, response: httpx.Response) -> bytes:
        encoding = response.headers.get("content-encoding", "identity").strip().lower()
        if encoding not in {"identity", "gzip"}:
            raise FeedFetchError("Unsupported Digitraffic encoding")
        declared = response.headers.get("content-length", "")
        if declared.isdigit() and int(declared) > self._max_bytes:
            raise FeedFetchError("Digitraffic compressed response exceeds byte limit")
        decoder = zlib.decompressobj(16 + zlib.MAX_WBITS) if encoding == "gzip" else None
        encoded_size, decoded_size = 0, 0
        chunks: list[bytes] = []
        try:
            async for chunk in response.aiter_raw():
                encoded_size += len(chunk)
                if encoded_size > self._max_bytes:
                    raise FeedFetchError("Digitraffic compressed response exceeds byte limit")
                decoded = (
                    decoder.decompress(chunk, self._max_bytes - decoded_size + 1)
                    if decoder
                    else chunk
                )
                decoded_size += len(decoded)
                if decoded_size > self._max_bytes:
                    raise FeedFetchError("Digitraffic decoded response exceeds byte limit")
                chunks.append(decoded)
            if decoder and (not decoder.eof or decoder.unused_data or decoder.unconsumed_tail):
                raise FeedFetchError("Invalid Digitraffic gzip stream")
        except zlib.error:
            raise FeedFetchError("Invalid Digitraffic gzip stream") from None
        return b"".join(chunks)
