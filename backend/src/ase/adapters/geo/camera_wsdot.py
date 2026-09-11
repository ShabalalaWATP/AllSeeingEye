"""WSDOT's official access-code catalogue, with public snapshots only.

Contract: https://www.wsdot.wa.gov/traffic/api/HighwayCameras/
HighwayCamerasREST.svc/help/operations/GetCamerasAsJson
"""

import json
from urllib.parse import urlencode

from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient
from ase.adapters.feeds.secret_urls import SecretFeedUrl
from ase.adapters.geo.camera_americas_parsers import parse_index
from ase.domain.cameras import Camera

ORIGIN = "https://www.wsdot.wa.gov"
ENDPOINT = f"{ORIGIN}/Traffic/api/HighwayCameras/HighwayCamerasREST.svc/GetCamerasAsJson"
SOURCE_URL = f"{ORIGIN}/traffic/api/"


class WsdotCameraSource:
    id = "wsdot"
    name = "WSDOT"

    def __init__(self, http: FeedHttpClient, access_code: str | None = None) -> None:
        self._http = http
        self._target: SecretFeedUrl | None = None
        if access_code:
            if len(access_code) > 512 or any(
                ord(char) < 33 or ord(char) > 126 for char in access_code
            ):
                raise ValueError("Invalid WSDOT access code configuration.")
            self._target = SecretFeedUrl(
                ORIGIN, f"{ENDPOINT}?" + urlencode({"AccessCode": access_code})
            )

    async def fetch(self) -> tuple[Camera, ...]:
        if self._target is None:
            # Keep the provider visible, without repeatedly requesting the retired index.
            raise ValueError("WSDOT cameras require ASE_WSDOT_ACCESS_CODE.")
        try:
            payload = await self._http.get_secret_bytes(self._target)
            cameras = parse_index(self.id, self.name, SOURCE_URL, json.loads(payload))
            if not cameras:
                raise ValueError("No usable cameras")
            return cameras
        except (FeedFetchError, ValueError, TypeError, RecursionError):
            # Never retain a credential-bearing URL or upstream response in a traceback.
            raise ValueError("WSDOT camera catalogue unavailable.") from None
