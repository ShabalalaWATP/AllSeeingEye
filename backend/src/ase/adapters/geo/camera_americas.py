"""OSIRIS Americas official public catalogues. Attribution: docs/CAMERA_AMERICAS.md."""

import json
from dataclasses import replace
from urllib.parse import urlencode

from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.geo.camera_americas_common import FRAME_HOSTS, MEDIA_HOSTS, camera, unique
from ase.adapters.geo.camera_americas_ibi import CONFIGS, IbiCameraSource
from ase.adapters.geo.camera_americas_parsers import parse_index
from ase.adapters.geo.camera_wsdot import WsdotCameraSource
from ase.application.ports.cameras import CameraSource
from ase.domain.cameras import Camera

__all__ = ["FRAME_HOSTS", "MEDIA_HOSTS", "build_sources"]

ENDPOINTS = {
    "caltrans": (
        "Caltrans",
        "https://caltrans-gis.dot.ca.gov/arcgis/rest/services/CHhighway/CCTV/FeatureServer/0/query?where=1%3D1&outFields=*&f=json&resultRecordCount=2000&orderByFields=OBJECTID",
    ),
    "ottawa": ("City of Ottawa", "https://traffic.ottawa.ca/beta/camera_list"),
    "quebec": (
        "Quebec 511",
        "https://ws.mapserver.transports.gouv.qc.ca/swtq?service=wfs&version=2.0.0&request=getfeature&typename=ms:infos_cameras&outfile=Camera&srsname=EPSG:4326&outputformat=geojson",
    ),
    "ontario": ("Ontario 511", "https://511on.ca/api/v2/get/cameras"),
    "alberta": ("Alberta 511", "https://511.alberta.ca/api/v2/get/cameras"),
    "montreal": (
        "Ville de Montreal",
        "https://ville.montreal.qc.ca/circulation/sites/ville.montreal.qc.ca.circulation/files/cameras.json",
    ),
    "toronto": (
        "City of Toronto",
        "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/a3309088-5fd4-4d34-8297-77c8301840ac/resource/4a568300-c7f8-496d-b150-dff6f5dc6d4f/download/traffic-camera-list-4326.geojson",
    ),
    "drivebc": ("DriveBC", "https://www.drivebc.ca/api/webcams/"),
    "illinois": ("Travel Midwest", "https://travelmidwest.com/lmiga/cameraReport.json"),
    "oregon": ("ODOT TripCheck", "https://www.tripcheck.com/Scripts/map/data/cctvinventory.js"),
    "michigan": ("MDOT MiDrive", "https://mdotjboss.state.mi.us/MiDrive/camera/list"),
}
QUERY = """query MapFeatures($input: MapFeaturesArgs!) {
 mapFeaturesQuery(input: $input) { mapFeatures { title uri features { geometry } __typename
 ... on Camera { active views(limit: 1) { category ... on CameraView { url } } } }
 error { message } } }"""
ENDPOINTS["indiana"] = (
    "INDOT TrafficWise",
    "https://511in.org/api/graphql?"
    + urlencode(
        {
            "query": QUERY,
            "variables": json.dumps(
                {
                    "input": {
                        "north": 41.9,
                        "south": 37.7,
                        "east": -84.6,
                        "west": -88.2,
                        "zoom": 16,
                        "layerSlugs": ["normalCameras"],
                        "nonClusterableUris": None,
                    }
                }
            ),
        }
    ),
)


class AmericanCameraSource:
    def __init__(self, provider: str, http: FeedHttpClient) -> None:
        self.id, self.http = provider, http
        self.name, self.url = ENDPOINTS[provider]

    async def fetch(self) -> tuple[Camera, ...]:
        data = json.loads(await self.http.get_bytes(self.url, conditional=False, max_redirects=0))
        if self.id == "caltrans":
            data = await self._caltrans_pages(data)
        cameras = parse_index(self.id, self.name, self.url.split("?")[0], data)
        if not cameras:
            raise ValueError("Provider returned no usable public cameras")
        return cameras

    async def _caltrans_pages(self, data: object) -> object:
        if not isinstance(data, dict) or not isinstance(data.get("features"), list):
            raise ValueError("Invalid Caltrans index")
        records = list(data["features"])
        more = data.get("exceededTransferLimit")
        while more and len(records) < 5000:
            size = min(2000, 5000 - len(records))
            url = self.url.replace("resultRecordCount=2000", f"resultRecordCount={size}")
            url += f"&resultOffset={len(records)}"
            page = json.loads(await self.http.get_bytes(url, conditional=False, max_redirects=0))
            if (
                not isinstance(page, dict)
                or not isinstance(page.get("features"), list)
                or not page["features"]
            ):
                raise ValueError("Incomplete Caltrans index")
            records.extend(page["features"][:size])
            more = page.get("exceededTransferLimit")
        if more:
            raise ValueError("Caltrans catalogue exceeds 5000-camera safety limit")
        return {"features": records}


class AmericanPublishedLinks:
    id = "us-published"
    name = "US published webcams"

    async def fetch(self) -> tuple[Camera, ...]:
        return tuple(
            replace(c, coordinate_precision="approximate")
            for c in unique(
                [
                    camera(
                        self.id,
                        "Butler County Sheriff",
                        "https://www.butlersheriff.org/",
                        "hamilton",
                        "Hamilton, Ohio",
                        39.3988617,
                        -84.5595353,
                        "https://gsccam.butlersheriff.org/axis-cgi/jpg/image.cgi",
                        external="https://gsccam.butlersheriff.org/camera/index.html#/video",
                    ),
                    camera(
                        self.id,
                        "Butler County Sheriff",
                        "https://www.butlersheriff.org/",
                        "oh129",
                        "OH-129 at 747",
                        39.381435,
                        -84.438423,
                        "https://towercam.butlersheriff.org/axis-cgi/jpg/image.cgi",
                        external="https://towercam.butlersheriff.org/aca/index.html#view",
                    ),
                    camera(
                        self.id,
                        "CincyVision",
                        "https://www.youtube.com/@AaronPreslin/live",
                        "cincyvision",
                        "CincyVision public livestream",
                        39.089101,
                        -84.527943,
                        external="https://www.youtube.com/@AaronPreslin/live",
                    ),
                    camera(
                        self.id,
                        "EarthCam",
                        "https://www.earthcam.com/usa/kentucky/covington/",
                        "covington",
                        "Cincinnati-Covington EarthCam",
                        39.090510,
                        -84.510413,
                        external="https://www.earthcam.com/usa/kentucky/covington/?cam=covington",
                    ),
                ]
            )
        )


def build_sources(
    http: FeedHttpClient, *, wsdot_access_code: str | None = None
) -> tuple[CameraSource, ...]:
    return (
        WsdotCameraSource(http, wsdot_access_code),
        *(AmericanCameraSource(provider, http) for provider in ENDPOINTS),
        *(IbiCameraSource(cfg, http) for cfg in CONFIGS),
        AmericanPublishedLinks(),
    )
