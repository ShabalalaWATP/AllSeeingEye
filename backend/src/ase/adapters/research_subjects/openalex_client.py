"""Optional OpenAlex Bearer authentication over the guarded feed transport.

Contract: https://help.openalex.org/api/authentication/
Credentials never enter URLs or shared HTTP headers; anonymous access remains supported.
"""

from typing import Any

from ase.adapters.feeds.http import FeedCredential, FeedHttpClient

OPENALEX_ORIGIN = "https://api.openalex.org"


class OpenAlexClient:
    def __init__(self, http: FeedHttpClient, api_key: str | None = None) -> None:
        self._http = http
        self._credential: FeedCredential | None = None
        if api_key:
            if len(api_key) > 512 or any(ord(char) < 33 or ord(char) > 126 for char in api_key):
                raise ValueError("Invalid OpenAlex API key configuration.")
            self._credential = FeedCredential(OPENALEX_ORIGIN, f"Bearer {api_key}")

    @property
    def authenticated(self) -> bool:
        return self._credential is not None

    async def get_json(self, url: str, *, conditional: bool = False, max_redirects: int = 0) -> Any:
        if self._credential is None:
            return await self._http.get_json(url, conditional=False, max_redirects=0)
        return await self._http.get_json(
            url, conditional=False, max_redirects=0, credential=self._credential
        )
