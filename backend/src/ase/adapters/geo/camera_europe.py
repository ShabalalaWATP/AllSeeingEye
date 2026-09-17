"""European public indexes and attributed OSIRIS reference catalogues.

Curated positions are approximate and media availability is not asserted.
Only fixed official catalogue URLs are fetched by the server.
"""

import json
import math
from importlib import import_module
from typing import Any
from urllib.parse import urlsplit

from ase.adapters.feeds.http import FeedHttpClient
from ase.application.ports.cameras import CameraSource
from ase.domain.cameras import Camera

COUNTRIES = (
    "bulgaria",
    "serbia",
    "macedonia",
    "romania",
    "italy",
    "czechia",
    "slovakia",
    "germany",
    "france",
    "spain",
    "poland",
    "switzerland",
)
ENDPOINTS = {
    "asfinag": "https://odo.asfinag.at/odo/rest/sec/resource/001/json/webcams?language=atDE",
    "netherlands": "https://api.rwsverkeersinfo.nl/api/cameras/",
    "iceland": "https://gagnaveita.vegagerdin.is/api/vefmyndavelar2014_1",
    "spain-dgt": "https://www.dgt.es/.content/.assets/json/camaras.json",
}
MEDIA_HOSTS = {
    "cdn.uab.org",
    "meteo.chavo.biz",
    "pics.smartburgas.eu",
    "stream.uzivobeograd.rs",
    "kamere.amss.org.rs",
    "streaming1.neotel.net.mk",
    "home-solutions.bg",
    "ls.tkchopin.pl",
    "www.slupsk.pl",
    "wc-heli.chuv.ch",
    "www.vegagerdin.is",
    "vefmyndavelar.vegagerdin.is",
    "infocar.dgt.es",
    "etraffic.dgt.es",
    "www.dgt.es",
    "stream.inmoves.nl",
    "webcams.asfinag.at",
}
FRAME_HOSTS = {"www.youtube.com", "ipcamlive.com"}
EXTERNAL_HOSTS = (
    MEDIA_HOSTS
    | FRAME_HOSTS
    | {
        "www.skylinewebcams.com",
        "voyage.aprr.fr",
        "www.weather-webcam.eu",
        "www.rwsverkeersinfo.nl",
        "www.asfinag.at",
        "www.vegagerdin.is",
    }
)
REFERENCE = "https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv"


def _url(value: Any, hosts: set[str]) -> str | None:
    if not isinstance(value, str) or len(value) > 2048:
        return None
    try:
        parts = urlsplit(value)
        if (
            parts.scheme == "https"
            and parts.netloc in hosts
            and not parts.fragment
            and not any(ord(c) < 33 for c in value)
        ):
            return value
    except ValueError:
        pass
    return None


def make_camera(provider: str, row: dict[str, Any], *, approximate: bool) -> Camera | None:
    """Validate even curated records; upstream fields cannot widen media origins."""
    try:
        lat, lon = float(row.get("lat", "nan")), float(row.get("lng", "nan"))
    except (TypeError, ValueError):
        return None
    if not (
        math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180
    ) or (lat == 0 and lon == 0):
        return None
    key = str(row.get("id") or "")
    if not key or len(key) > 160:
        return None
    image = _url(row.get("feed_url"), MEDIA_HOSTS)
    kind = row.get("stream_type")
    stream = _url(row.get("stream_url"), FRAME_HOSTS if kind == "iframe" else MEDIA_HOSTS)
    if kind not in {"hls", "mp4", "mjpeg", "iframe"}:
        stream = None
    external = _url(row.get("external_url"), EXTERNAL_HOSTS)
    if not (image or stream or external):
        return None
    return Camera(
        id=f"{provider}:{key}",
        provider=provider,
        title=str(row.get("name") or provider)[:240],
        latitude=lat,
        longitude=lon,
        snapshot_url=image,
        source_url=external or ENDPOINTS.get(provider, REFERENCE),
        attribution=f"Source: {row.get('source', provider)}. Provider terms apply."
        + (
            " OSIRIS reference location, approximate; availability not verified."
            if approximate
            else ""
        ),
        stream_url=stream,
        stream_type=kind if stream else None,
        external_url=external,
        coordinate_precision="approximate" if approximate else "exact",
    )


def curated(provider: str) -> tuple[Camera, ...]:
    if provider == "greece":
        rows = [
            {
                "id": alias,
                "lat": lat,
                "lng": lon,
                "name": name,
                "source": "Attiki Odos",
                "stream_type": "iframe",
                "stream_url": f"https://ipcamlive.com/player/player.php?alias={alias}",
            }
            for alias, name, lat, lon in (
                ("cam128", "I/C D. Plakentias", 38.0208, 23.8578),
                ("cam231", "I/C Papagou", 37.9906, 23.7947),
            )
        ]
    else:
        if provider not in COUNTRIES:
            raise ValueError("Unknown curated camera provider")
        # Only fixed bundled catalogue modules in COUNTRIES can be imported.
        # nosemgrep: python.lang.security.audit.non-literal-import.non-literal-import
        rows = json.loads(import_module(f"ase.adapters.geo.camera_europe_{provider}").DATA)
    cameras = [make_camera(provider, row, approximate=True) for row in rows[:5000]]
    return tuple({cam.id: cam for cam in cameras if cam is not None}.values())


def parse_index(provider: str, payload: bytes) -> tuple[Camera, ...]:
    data = json.loads(payload)
    if provider == "spain-dgt" and isinstance(data, dict):
        data = data.get("camaras")
    if not isinstance(data, list):
        raise ValueError("Invalid public camera catalogue")
    result = {}
    for index, item in enumerate(data[:5000]):
        if not isinstance(item, dict):
            continue
        row = _index_row(provider, item, index)
        camera = make_camera(provider, row, approximate=False)
        if camera:
            result[camera.id] = camera
    return tuple(result.values())


def _index_row(provider: str, item: dict[str, Any], index: int) -> dict[str, Any]:
    if provider == "netherlands":
        # RWS snapshots require a Referer. Offer its public player externally,
        # without bypassing its current player authorisation or hotlink protection.
        return {
            "id": item.get("id"),
            "lat": item.get("latitude"),
            "lng": item.get("longitude"),
            "name": item.get("location_description")
            or f"{item.get('road', '')} {item.get('near', '')}",
            "external_url": item.get("stream_url"),
            "source": "Rijkswaterstaat",
        }
    if provider == "iceland":
        image = item.get("Slod", "")
        if isinstance(image, str) and image.startswith("/"):
            image = "https://www.vegagerdin.is" + image
        return {
            "id": f"{item.get('Maelist_nr')}-{index}",
            "lat": item.get("Breidd"),
            "lng": item.get("Lengd"),
            "name": f"{item.get('Myndavel')} {item.get('Skyring')}",
            "feed_url": image,
            "source": "Vegagerðin",
        }
    if provider == "spain-dgt":
        return {
            "id": item.get("id"),
            "lat": item.get("latitud"),
            "lng": item.get("longitud"),
            "name": f"{item.get('carretera')} km {item.get('pk')}",
            "feed_url": item.get("imagen"),
            "source": "DGT",
        }
    return {
        "id": item.get("wcs_id"),
        "lat": item.get("wgs84_lat"),
        "lng": item.get("wgs84_lon"),
        "name": item.get("position_txt"),
        "feed_url": item.get("url_campic"),
        "source": "ASFINAG",
    }


class EuropeanCameraSource:
    def __init__(self, provider: str, http: FeedHttpClient) -> None:
        self.id = provider
        self.name = {
            "asfinag": "ASFINAG (Austria)",
            "netherlands": "Rijkswaterstaat",
            "iceland": "Vegagerðin (Iceland)",
            "spain-dgt": "DGT (Spain)",
            "macedonia": "North Macedonia",
        }.get(provider, provider.title())
        self._http = http

    async def fetch(self) -> tuple[Camera, ...]:
        if self.id == "turkey":
            raise ValueError("OSIRIS removed Turkish cameras because embedding was restricted")
        if self.id in ENDPOINTS:
            payload = await self._http.get_bytes(
                ENDPOINTS[self.id],
                conditional=False,
                max_redirects=0,
            )
            cameras = parse_index(self.id, payload)
            if not cameras:
                raise ValueError("Public catalogue returned no supported camera links")
            return cameras
        return curated(self.id)


def build_sources(http: FeedHttpClient) -> tuple[CameraSource, ...]:
    return tuple(
        EuropeanCameraSource(name, http) for name in (*ENDPOINTS, *COUNTRIES, "greece", "turkey")
    )
