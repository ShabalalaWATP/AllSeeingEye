"""Bounded public camera queries, including read-only JSON POST catalogue APIs."""

import json
from typing import Any

import httpx

from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient, assert_public_host


class CameraHttpClient(FeedHttpClient):
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
