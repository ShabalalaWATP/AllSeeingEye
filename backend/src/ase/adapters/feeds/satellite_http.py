"""Distinguish CelesTrak's documented unchanged-data 403 from an access refusal."""

from urllib.parse import urlsplit

import httpx

from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient, FeedHttpStatusError


class ElementsNotUpdated(FeedFetchError):
    """Provider has already served this update to this public IP."""


class SatelliteHttpClient(FeedHttpClient):
    async def _status_error(self, response: httpx.Response, url: str) -> FeedFetchError:
        parts = urlsplit(url)
        if (
            response.status_code == 403
            and parts.scheme == "https"
            and parts.netloc == "celestrak.org"
            and parts.path == "/NORAD/elements/gp.php"
            and response.headers.get("content-encoding", "identity").strip().lower() == "identity"
        ):
            # Never retain or publish provider HTML, IP addresses or arbitrary error text.
            prefix = bytearray()
            async for chunk in response.aiter_bytes():
                prefix.extend(chunk[: 4096 - len(prefix)])
                if len(prefix) >= 4096:
                    break
            if b"GP data has not updated since your last successful" in prefix:
                return ElementsNotUpdated("CelesTrak has no newer orbital elements yet")
        return FeedHttpStatusError(response.status_code, url)
