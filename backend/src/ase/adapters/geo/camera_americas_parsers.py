"""Public American transport camera index parsers, no source HTML is rendered."""

import re
from html import unescape
from typing import Any
from urllib.parse import quote, urlencode, urljoin

from ase.adapters.geo.camera_americas_common import camera, unique
from ase.domain.cameras import Camera


def obj(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def rows(value: Any) -> list[Any]:
    return value[:5000] if isinstance(value, list) else []


def first(value: Any) -> dict[str, Any]:
    items = rows(value)
    return obj(items[0]) if items else {}


def coords(value: Any) -> tuple[Any, Any]:
    values = rows(value)
    if values and isinstance(values[0], list):
        values = values[0]
    return (values[1], values[0]) if len(values) >= 2 else (None, None)


def parse_index(provider: str, name: str, source: str, data: Any) -> tuple[Camera, ...]:
    if provider == "indiana":
        data = obj(obj(obj(data).get("data")).get("mapFeaturesQuery")).get("mapFeatures")
    elif provider == "illinois":
        data = obj(data).get("cameraReports", data)
    elif provider in ("caltrans", "oregon", "toronto", "quebec"):
        data = obj(data).get("features")
    if not isinstance(data, list):
        raise ValueError("Camera index does not contain records")
    return unique([parse_row(provider, name, source, obj(item)) for item in data[:5000]])


def _western(provider: str, r: dict[str, Any]) -> dict[str, Any] | None:
    key: Any = None
    title: Any = None
    lat: Any = None
    lon: Any = None
    image: Any = None
    stream: Any = None
    external: Any = None
    stream_type = "hls"
    if provider in ("caltrans", "oregon"):
        p = obj(r.get("attributes"))
        lat, lon = p.get("latitude"), p.get("longitude")
        if provider == "caltrans":
            if str(p.get("inService")).lower() == "false":
                return None
            key, title, image = p.get("OBJECTID"), p.get("locationName"), p.get("currentImageURL")
            value = p.get("streamingVideoURL")
            if isinstance(value, str) and re.search(r"\.m3u8(?:\?|$)", value):
                stream = value
        else:
            key, title = p.get("cameraId"), p.get("title")
            filename = p.get("filename")
            if isinstance(filename, str) and re.fullmatch(r"[A-Za-z0-9_ .@()-]{1,240}", filename):
                image = "https://tripcheck.com/RoadCams/cams/" + quote(filename, safe="")
    return {
        "key": key,
        "title": title,
        "lat": lat,
        "lon": lon,
        "snapshot": image,
        "stream": stream,
        "stream_type": stream_type,
        "external": external,
    }


def _simple(provider: str, r: dict[str, Any]) -> dict[str, Any] | None:
    key: Any = None
    title: Any = None
    lat: Any = None
    lon: Any = None
    image: Any = None
    stream: Any = None
    external: Any = None
    stream_type = "hls"
    if provider == "wsdot":
        if r.get("IsActive") is False:
            return None
        key, title, image = r.get("CameraID"), r.get("Title"), r.get("ImageURL")
        p = obj(r.get("CameraLocation"))
        lat, lon = p.get("Latitude"), p.get("Longitude")
    elif provider == "ottawa":
        key, title, lat, lon = (
            r.get("id"),
            r.get("description"),
            r.get("latitude"),
            r.get("longitude"),
        )
        number = r.get("number", key)
        if type(number) is int:
            image = f"https://traffic.ottawa.ca/map/camera?id={number}"
    elif provider in ("ontario", "alberta"):
        key, title, lat, lon = r.get("Id"), r.get("Location"), r.get("Latitude"), r.get("Longitude")
        view = next((obj(v) for v in rows(r.get("Views")) if obj(v).get("Status") == "Enabled"), {})
        image = view.get("Url")
    return {
        "key": key,
        "title": title,
        "lat": lat,
        "lon": lon,
        "snapshot": image,
        "stream": stream,
        "stream_type": stream_type,
        "external": external,
    }


def _canadian(provider: str, r: dict[str, Any]) -> dict[str, Any] | None:
    key: Any = None
    title: Any = None
    lat: Any = None
    lon: Any = None
    image: Any = None
    stream: Any = None
    external: Any = None
    stream_type = "hls"
    if provider in ("quebec", "toronto"):
        p = obj(r.get("properties"))
        lat, lon = coords(obj(r.get("geometry")).get("coordinates"))
        if provider == "quebec":
            key = p.get("IDEcamera")
            title = p.get("DescriptionLocalisationEn") or p.get("DescriptionLocalisationFr")
            if isinstance(key, str) and key.isdigit():
                stream = (
                    f"https://www.quebec511.info/Carte/Fenetres/camera.ashx?id={key}&format=mp4"
                )
                stream_type = "mp4"
                external = f"https://www.quebec511.info/Carte/Fenetres/FenetreVideo.html?id={key}"
        else:
            key, title, image = (
                p.get("REC_ID"),
                f"{p.get('MAINROAD', '')} / {p.get('CROSSROAD', '')}",
                p.get("IMAGEURL"),
            )
    elif provider == "drivebc":
        key, title = r.get("id"), r.get("name") or r.get("caption")
        lat, lon = coords(obj(r.get("location")).get("coordinates"))
        path = obj(r.get("links")).get("imageDisplay")
        image = urljoin("https://www.drivebc.ca", path) if isinstance(path, str) else None
    return {
        "key": key,
        "title": title,
        "lat": lat,
        "lon": lon,
        "snapshot": image,
        "stream": stream,
        "stream_type": stream_type,
        "external": external,
    }


def _michigan(provider: str, r: dict[str, Any]) -> dict[str, Any] | None:
    key: Any = None
    title: Any = None
    lat: Any = None
    lon: Any = None
    image: Any = None
    stream: Any = None
    external: Any = None
    stream_type = "hls"
    if provider == "michigan":
        county = unescape(str(r.get("county", "")))
        position = re.search(r"lat=(-?[\d.]+)&lon=(-?[\d.]+)", county)
        identity = re.search(r"[?&]id=(\d+)", county)
        picture = re.search(r'src="(https://[^\"]+)"', str(r.get("image", "")))
        if not position or not identity or not picture:
            return None
        key, lat, lon, image = identity[1], position[1], position[2], unescape(picture[1])
        title = re.sub(r"<[^>]*>", "", str(r.get("route", "")) + " " + str(r.get("location", "")))
    return {
        "key": key,
        "title": title,
        "lat": lat,
        "lon": lon,
        "snapshot": image,
        "stream": stream,
        "stream_type": stream_type,
        "external": external,
    }


def _indiana(provider: str, r: dict[str, Any]) -> dict[str, Any] | None:
    key: Any = None
    title: Any = None
    lat: Any = None
    lon: Any = None
    image: Any = None
    stream: Any = None
    external: Any = None
    stream_type = "hls"
    if provider == "indiana":
        if r.get("__typename") != "Camera" or r.get("active") is False:
            return None
        image = first(r.get("views")).get("url")
        token = re.fullmatch(
            r"https://public\.carsprogram\.org/cameras/IN/(INDOT_\d+_[A-Za-z0-9_-]+)\.flv\.png",
            str(image),
        )
        identity = re.fullmatch(r"camera/(\d+)", str(r.get("uri")))
        if not token or not identity:
            return None
        lat, lon = coords(obj(first(r.get("features")).get("geometry")).get("coordinates"))
        key, title = identity[1], unescape(str(r.get("title", "")))
        stream = f"https://skysfs4.trafficwise.org/preroll/{token[1]}/playlist.m3u8"
        external = "https://511in.org/?" + urlencode({"show": r["uri"]})
    return {
        "key": key,
        "title": title,
        "lat": lat,
        "lon": lon,
        "snapshot": image,
        "stream": stream,
        "stream_type": stream_type,
        "external": external,
    }


def _legacy(provider: str, r: dict[str, Any]) -> dict[str, Any] | None:
    key: Any = None
    title: Any = None
    lat: Any = None
    lon: Any = None
    image: Any = None
    stream: Any = None
    external: Any = None
    stream_type = "hls"
    if provider in ("montreal", "illinois"):
        key = r.get("id") or r.get("cameraId")
        title = r.get("description") or r.get("cameraName") or r.get("name")
        lat, lon = r.get("latitude", r.get("lat")), r.get("longitude", r.get("lng"))
        image = r.get("imageUrl") or r.get("url")
    return {
        "key": key,
        "title": title,
        "lat": lat,
        "lon": lon,
        "snapshot": image,
        "stream": stream,
        "stream_type": stream_type,
        "external": external,
    }


def parse_row(provider: str, name: str, source: str, r: dict[str, Any]) -> Camera | None:
    parsers = {
        "caltrans": _western,
        "oregon": _western,
        "wsdot": _simple,
        "ottawa": _simple,
        "ontario": _simple,
        "alberta": _simple,
        "quebec": _canadian,
        "toronto": _canadian,
        "drivebc": _canadian,
        "michigan": _michigan,
        "indiana": _indiana,
        "montreal": _legacy,
        "illinois": _legacy,
    }
    values = parsers[provider](provider, r)
    return camera(provider, name, source, **values, bounds=(15, 84, -170, -50)) if values else None
