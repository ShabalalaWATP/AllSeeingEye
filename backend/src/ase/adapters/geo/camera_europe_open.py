"""Official keyless European camera indexes published as JSON. See docs/CAMERA_EUROPE.md.

Lithuania (eismoinfo.lt), Ireland (TII on the CARS platform), Norway (Statens vegvesen road
weather and camera API, which requires a public `X-System-ID`), Hungary (Utinform) and
Autostrade per l'Italia. Positions come from each index; images load from exact hosts.
"""

import json
import math
import time
from collections.abc import Callable
from typing import Any

from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.geo.camera_curated import HostPolicy, collect
from ase.adapters.geo.camera_http import CameraHttpClient
from ase.application.ports.cameras import CameraSource
from ase.domain.cameras import Camera

ENDPOINTS = {
    "lithuania": "https://eismoinfo.lt/eismoinfo-backend/camera-info-table",
    "ireland": "https://iretg.carsprogram.org/cameras_v1/api/cameras",
    "norway": "https://road-weather-and-view.atlas.vegvesen.no/weather-information/measurement-sites",
    "hungary": "https://www.utinform.hu/api/public/webcam/all",
    "autostrade": "https://viabilita.autostrade.it/json/webcams.json",
}
NAMES = {
    "lithuania": "Lietuvos automobiliu keliu direkcija (eismoinfo.lt)",
    "ireland": "Transport Infrastructure Ireland",
    "norway": "Statens vegvesen (Norway)",
    "hungary": "Magyar Kozut Utinform (Hungary)",
    "autostrade": "Autostrade per l'Italia",
}
PAGES = {
    "lithuania": "https://eismoinfo.lt/",
    "ireland": "https://www.tiitraffic.ie/",
    "norway": "https://www.vegvesen.no/trafikk/",
    "hungary": "https://www.utinform.hu/",
    "autostrade": "https://www.autostrade.it/it/viaggia-sicuro/webcam",
}
MEDIA_HOSTS = frozenset(
    {
        "eismoinfo.lt",
        "irecam.carsprogram.org",
        "kamera.atlas.vegvesen.no",
        "kamera.vegvesen.no",
        "cdnuiwebcams.utinform.hu",
        "video.autostrade.it",
    }
)
POLICY = HostPolicy(MEDIA_HOSTS, frozenset(), MEDIA_HOSTS, NAMES, PAGES)
SYSTEM_ID = "theallseeingeye"
HUNGARY_FRESH_MS = 15 * 60 * 1000
AUTOSTRADE_FRAMES = "https://video.autostrade.it/video-frames/"
AUTOSTRADE_CLIPS = "https://video.autostrade.it/video-mp4_hq/"


def lks94_to_wgs84(x: float, y: float) -> tuple[float, float]:
    """Inverse transverse Mercator for LKS-94 (EPSG:3346): GRS80, 24 E, k 0.9998, 500 km east."""
    a, f, k0 = 6378137.0, 1 / 298.257222101, 0.9998
    e2 = f * (2 - f)
    ep2 = e2 / (1 - e2)
    m = y / k0
    mu = m / (a * (1 - e2 / 4 - 3 * e2**2 / 64 - 5 * e2**3 / 256))
    e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))
    phi1 = (
        mu
        + (3 * e1 / 2 - 27 * e1**3 / 32) * math.sin(2 * mu)
        + (21 * e1**2 / 16 - 55 * e1**4 / 32) * math.sin(4 * mu)
        + (151 * e1**3 / 96) * math.sin(6 * mu)
        + (1097 * e1**4 / 512) * math.sin(8 * mu)
    )
    sin1, cos1, tan1 = math.sin(phi1), math.cos(phi1), math.tan(phi1)
    n1 = a / math.sqrt(1 - e2 * sin1**2)
    t1, c1 = tan1**2, ep2 * cos1**2
    r1 = a * (1 - e2) / (1 - e2 * sin1**2) ** 1.5
    d = (x - 500000.0) / (n1 * k0)
    lat = phi1 - (n1 * tan1 / r1) * (
        d**2 / 2
        - (5 + 3 * t1 + 10 * c1 - 4 * c1**2 - 9 * ep2) * d**4 / 24
        + (61 + 90 * t1 + 298 * c1 + 45 * t1**2 - 252 * ep2 - 3 * c1**2) * d**6 / 720
    )
    lon = (
        d
        - (1 + 2 * t1 + c1) * d**3 / 6
        + (5 - 2 * c1 + 28 * t1 - 3 * c1**2 + 8 * ep2 + 24 * t1**2) * d**5 / 120
    ) / cos1
    return math.degrees(lat), 24.0 + math.degrees(lon)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value[:5000] if isinstance(value, list) else []


def parse_lithuania(data: Any) -> list[dict[str, Any]]:
    rows = []
    for item in map(_dict, _list(data)):
        try:
            lat, lon = lks94_to_wgs84(float(item["x"]), float(item["y"]))
        except (KeyError, TypeError, ValueError):
            continue
        if not (53.8 <= lat <= 56.5 and 20.9 <= lon <= 26.9):
            continue
        rows.append(
            {"id": item.get("id"), "name": item.get("name"), "lat": lat, "lng": lon}
            | {"feed_url": item.get("image")}
        )
    return rows


def parse_ireland(data: Any) -> list[dict[str, Any]]:
    rows = []
    for item in map(_dict, _list(data)):
        if item.get("public") is False:
            continue
        location = _dict(item.get("location"))
        for index, view in enumerate(map(_dict, _list(item.get("views")))):
            if view.get("type") != "STILL_IMAGE":
                continue
            rows.append(
                {
                    "id": f"{item.get('id')}-{index}",
                    "name": view.get("name") or item.get("name"),
                    "lat": location.get("latitude"),
                    "lng": location.get("longitude"),
                    "feed_url": view.get("url"),
                }
            )
    return rows


def parse_norway(data: Any) -> list[dict[str, Any]]:
    rows = []
    for feature in map(_dict, _list(_dict(data).get("features"))):
        props = _dict(feature.get("properties"))
        coordinates = _list(_dict(feature.get("geometry")).get("coordinates"))
        if len(coordinates) < 2:
            continue
        for cam in map(_dict, _list(props.get("cameras"))):
            if cam.get("status") != "OK":
                continue
            video = cam.get("videoUrl")
            view = cam.get("orientationDescription")
            rows.append(
                {
                    "id": cam.get("id"),
                    "name": f"{props.get('name')} (towards {view})" if view else props.get("name"),
                    "lat": coordinates[1],
                    "lng": coordinates[0],
                    "feed_url": cam.get("stillImageUrl"),
                }
                | ({"stream_url": video, "stream_type": "hls"} if video else {})
            )
    return rows


def parse_hungary(data: Any, now_ms: float) -> list[dict[str, Any]]:
    """Utinform only shows images newer than 15 minutes; older cameras are left out."""
    rows = []
    for feature in map(_dict, _list(_dict(data).get("features"))):
        props = _dict(feature.get("properties"))
        coordinates = _list(_dict(feature.get("geometry")).get("coordinates"))
        if not props.get("active") or not props.get("published") or len(coordinates) < 2:
            continue
        for cam in map(_dict, _list(props.get("webcams"))):
            place, number, last = (
                cam.get("cameraPlaceId"),
                cam.get("cameraNum"),
                cam.get("lastImage"),
            )
            if not cam.get("published") or not isinstance(last, int | float):
                continue
            if now_ms - last > HUNGARY_FRESH_MS or not str(place).isalnum():
                continue
            if type(number) is not int:
                continue
            towards = cam.get("cameraView")
            rows.append(
                {
                    "id": f"{place}_{number}",
                    "name": f"{props.get('placeName')} (towards {towards})"
                    if towards
                    else props.get("placeName"),
                    "lat": coordinates[1],
                    "lng": coordinates[0],
                    "feed_url": f"https://cdnuiwebcams.utinform.hu/webcamimages/{place}_{number}.jpg",
                }
            )
    return rows


def parse_autostrade(data: Any) -> list[dict[str, Any]]:
    rows = []
    for cam in map(_dict, _list(_dict(data).get("webcams"))):
        frames = _dict(cam.get("frames"))
        still = _dict(frames.get("F_0")).get("t_url") or _dict(frames.get("T")).get("t_url")
        clip = _dict(frames.get("V")).get("t_url")
        still_ok = isinstance(still, str) and ".." not in still
        clip_ok = isinstance(clip, str) and ".." not in clip and clip.endswith(".mp4")
        rows.append(
            {
                "id": cam.get("c_tel"),
                "name": cam.get("t_des_pub"),
                "lat": cam.get("n_crd_lat"),
                "lng": cam.get("n_crd_lon"),
                "feed_url": AUTOSTRADE_FRAMES + str(still) if still_ok else None,
            }
            | (
                {"stream_url": AUTOSTRADE_CLIPS + str(clip), "stream_type": "mp4"}
                if clip_ok
                else {}
            )
        )
    return rows


PARSERS: dict[str, Callable[[Any], list[dict[str, Any]]]] = {
    "lithuania": parse_lithuania,
    "ireland": parse_ireland,
    "norway": parse_norway,
    "hungary": lambda data: parse_hungary(data, time.time() * 1000),
    "autostrade": parse_autostrade,
}


def parse(provider: str, payload: bytes) -> tuple[Camera, ...]:
    cameras = collect(POLICY, provider, PARSERS[provider](json.loads(payload)), approximate=False)
    if not cameras:
        raise ValueError(f"{NAMES[provider]} returned no usable public cameras")
    return cameras


class OpenEuropeSource:
    def __init__(self, provider: str, http: FeedHttpClient) -> None:
        self.id, self.name, self.http = provider, NAMES[provider], http

    async def fetch(self) -> tuple[Camera, ...]:
        url = ENDPOINTS[self.id]
        if self.id == "norway":
            if not isinstance(self.http, CameraHttpClient):
                raise ValueError("Norwegian cameras need the camera HTTP client")
            payload = await self.http.get_identified(url, SYSTEM_ID)
        else:
            payload = await self.http.get_bytes(url, conditional=False, max_redirects=0)
        return parse(self.id, payload)


def build_sources(http: FeedHttpClient) -> tuple[CameraSource, ...]:
    return tuple(OpenEuropeSource(provider, http) for provider in ENDPOINTS)
