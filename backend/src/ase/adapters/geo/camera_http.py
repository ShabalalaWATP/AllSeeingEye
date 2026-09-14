"""Bounded public camera queries, including read-only JSON POST catalogue APIs."""

import json
import re
from typing import Any

import httpx

from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient, assert_public_host

SYSTEM_ID = re.compile(r"[A-Za-z0-9._-]{1,64}")


class CameraHttpClient(FeedHttpClient):
    async def get_identified(self, url: str, system_id: str) -> bytes:
        """GET for an upstream that requires a public client identifier, never a secret.

        Statens vegvesen answers 400 without `X-System-ID`; any stable name is accepted.
        """
        if SYSTEM_ID.fullmatch(system_id) is None:
            raise ValueError("Invalid system identifier")
        address = await assert_public_host(url)
        headers = {"Accept-Encoding": "identity", "X-System-ID": system_id}
        target, extensions = self._pinned(url, address, headers)
        try:
            async with self._client.stream(
                "GET", target, headers=headers, extensions=extensions, follow_redirects=False
            ) as response:
                if response.status_code >= 300:
                    raise FeedFetchError("Camera catalogue refused")
                return await self._read_bounded(response)
        except httpx.HTTPError as exc:
            raise FeedFetchError("Camera catalogue request failed") from exc

    async def post_json(self, url: str, payload: dict[str, Any]) -> Any:
        # Only fixed source adapters call this primitive; no caller supplies URLs.
        body = json.dumps(payload).encode()
        if len(body) > 65536:
            raise FeedFetchError("Camera query exceeds request limit")
        address = await assert_public_host(url)
        headers = {"Accept-Encoding": "identity", "Content-Type": "application/json"}
        target, extensions = self._pinned(url, address, headers)
        try:
            async with self._client.stream(
                "POST",
                target,
                content=body,
                headers=headers,
                extensions=extensions,
                follow_redirects=False,
            ) as response:
                if response.status_code >= 300:
                    raise FeedFetchError("Camera query refused")
                return json.loads(await self._read_bounded(response))
        except (httpx.HTTPError, ValueError, RecursionError) as exc:
            raise FeedFetchError("Camera query failed") from exc
