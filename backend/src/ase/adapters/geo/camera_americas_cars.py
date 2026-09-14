"""Public Castle Rock CARS 511 map catalogues (keyless GraphQL GET). See docs/CAMERA_AMERICAS.md.

Indiana keeps its own parser because its stream URLs are derived from the image name. These
states publish the snapshot URL, and some publish an HLS source, directly in each view.
"""

import json
import re
from dataclasses import dataclass
from html import unescape
from typing import Any
from urllib.parse import urlencode, urlsplit

from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.geo.camera_americas_common import camera, unique
from ase.adapters.geo.camera_americas_parsers import coords, first, obj, rows
from ase.domain.cameras import Camera

QUERY = """query MapFeatures($input: MapFeaturesArgs!) {
 mapFeaturesQuery(input: $input) { mapFeatures { title uri features { geometry } __typename
 ... on Camera { active views(limit: 1) { category
 ... on CameraView { url sources { type src } } } } }
 error { message } } }"""


@dataclass(frozen=True)
class CarsConfig:
    id: str
    name: str
    base: str
    bounds: tuple[float, float, float, float]
    # Streams are offered only from hosts that answered with open CORS and unsigned URLs.
    stream_hosts: frozenset[str] = frozenset()


CONFIGS = (
    CarsConfig(
        "minnesota",
        "MnDOT 511",
        "https://511mn.org",
        (43.4, 49.5, -97.3, -89.4),
        frozenset({"video.dot.state.mn.us"}),
    ),
    CarsConfig("iowa", "Iowa 511", "https://www.511ia.org", (40.3, 43.6, -96.7, -90.1)),
    CarsConfig("kansas", "KanDrive", "https://www.kandrive.gov", (36.9, 40.1, -102.1, -94.5)),
    CarsConfig("massachusetts", "Mass511", "https://mass511.com", (41.2, 42.9, -73.6, -69.8)),
)


def catalogue_url(cfg: CarsConfig) -> str:
    south, north, west, east = cfg.bounds
    area = {"north": north, "south": south, "east": east, "west": west, "zoom": 16}
    variables = {"input": {**area, "layerSlugs": ["normalCameras"], "nonClusterableUris": None}}
    return f"{cfg.base}/api/graphql?" + urlencode(
        {"query": QUERY, "variables": json.dumps(variables)}
    )


def parse_feature(cfg: CarsConfig, row: Any) -> Camera | None:
    r = obj(row)
    if r.get("__typename") != "Camera" or r.get("active") is False:
        return None
    identity = re.fullmatch(r"camera/(\d{1,12})", str(r.get("uri")))
    if not identity:
        return None
    view = first(r.get("views"))
    stream = None
    for source in rows(view.get("sources")):
        src = obj(source).get("src")
        if (
            obj(source).get("type") == "application/x-mpegURL"
            and isinstance(src, str)
            and urlsplit(src).hostname in cfg.stream_hosts
            and not urlsplit(src).query
        ):
            stream = src
            break
    lat, lon = coords(obj(first(r.get("features")).get("geometry")).get("coordinates"))
    return camera(
        cfg.id,
        cfg.name,
        cfg.base,
        identity[1],
        unescape(str(r.get("title") or "")),
        lat,
        lon,
        view.get("url"),
        stream=stream,
        bounds=cfg.bounds,
        external=f"{cfg.base}/?" + urlencode({"show": r["uri"]}),
    )


def parse_catalogue(cfg: CarsConfig, data: Any) -> tuple[Camera, ...]:
    query = obj(obj(obj(data).get("data")).get("mapFeaturesQuery"))
    features = query.get("mapFeatures")
    if not isinstance(features, list):
        raise ValueError("Invalid CARS camera catalogue")
    return unique([parse_feature(cfg, row) for row in features[:5000]])


class CarsCameraSource:
    def __init__(self, cfg: CarsConfig, http: FeedHttpClient) -> None:
        self.id, self.name, self.cfg, self.http = cfg.id, cfg.name, cfg, http

    async def fetch(self) -> tuple[Camera, ...]:
        body = await self.http.get_bytes(
            catalogue_url(self.cfg), conditional=False, max_redirects=0
        )
        cameras = parse_catalogue(self.cfg, json.loads(body))
        if not cameras:
            raise ValueError("Provider returned no usable public cameras")
        return cameras
