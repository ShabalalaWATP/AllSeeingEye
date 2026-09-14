"""Americas camera boundaries. Source attribution: docs/CAMERA_AMERICAS.md."""

import math
import re
from typing import Any, Literal, cast
from urllib.parse import urlsplit

from ase.domain.cameras import Camera

MEDIA_HOSTS = {
    "images.wsdot.wa.gov",
    "cwwp2.dot.ca.gov",
    "wzmedia.dot.ca.gov",
    "traffic.ottawa.ca",
    "www.quebec511.info",
    "511on.ca",
    "511.alberta.ca",
    "opendata.toronto.ca",
    "drivebc.ca",
    "images.drivebc.ca",
    "www.drivebc.ca",
    "ville.montreal.qc.ca",
    "www.travelmidwest.com",
    "travelmidwest.com",
    "tripcheck.com",
    "www.tripcheck.com",
    "micamerasimages.net",
    "prod-ut.ibi511.com",
    "www.nvroads.com",
    "511la.org",
    "fl511.com",
    "511ga.org",
    "drivenc.gov",
    "www.drivenc.gov",
    "az511.gov",
    "itsstreamingbr.dotd.la.gov",
    "itsstreamingbr2.dotd.la.gov",
    "itsstreamingno.dotd.la.gov",
    "d1wse1.its.nv.gov",
    "d1wse2.its.nv.gov",
    "d1wse3.its.nv.gov",
    "d1wse4.its.nv.gov",
    "d1wse5.its.nv.gov",
    "d2wse1.its.nv.gov",
    "d2wse2.its.nv.gov",
    "d3wse1.its.nv.gov",
    "public.carsprogram.org",
    "skysfs4.trafficwise.org",
    "511in.org",
    "gsccam.butlersheriff.org",
    "towercam.butlersheriff.org",
    "511ny.org",
    "www.511pa.com",
    "newengland511.org",
    "511.idaho.gov",
    "ctroads.org",
    "511.alaska.gov",
    "511.novascotia.ca",
    "511.gnb.ca",
    "hotline.gov.sk.ca",
    "511nl.ca",
    "511yukon.ca",
    "www.manitoba511.ca",
    "s7.nysdot.skyvdn.com",
    "s9.nysdot.skyvdn.com",
    "s51.nysdot.skyvdn.com",
    "s52.nysdot.skyvdn.com",
    "s53.nysdot.skyvdn.com",
    "atmsqf.iowadot.gov",
    "kscam.carsprogram.org",
    "video.dot.state.mn.us",
    "www.kcscout.net",
}
FRAME_HOSTS: set[str] = set()
EXTERNAL_HOSTS = MEDIA_HOSTS | {
    "www.youtube.com",
    "www.earthcam.com",
    "mdotjboss.state.mi.us",
    # CARS 511 operator map pages, linked per camera; never loaded as media.
    "511mn.org",
    "www.511ia.org",
    "www.kandrive.gov",
    "mass511.com",
}

PROVIDER_HOSTS = {
    "wsdot": {"images.wsdot.wa.gov"},
    "caltrans": {"cwwp2.dot.ca.gov", "wzmedia.dot.ca.gov"},
    "ottawa": {"traffic.ottawa.ca"},
    "quebec": {"www.quebec511.info"},
    "ontario": {"511on.ca"},
    "alberta": {"511.alberta.ca"},
    "toronto": {"opendata.toronto.ca"},
    "drivebc": {"drivebc.ca", "www.drivebc.ca", "images.drivebc.ca"},
    "montreal": {"ville.montreal.qc.ca"},
    "illinois": {"travelmidwest.com", "www.travelmidwest.com"},
    "oregon": {"tripcheck.com", "www.tripcheck.com"},
    "michigan": {"micamerasimages.net"},
    "utah": {"prod-ut.ibi511.com"},
    "nevada": {
        "www.nvroads.com",
        "d1wse1.its.nv.gov",
        "d1wse2.its.nv.gov",
        "d1wse3.its.nv.gov",
        "d1wse4.its.nv.gov",
        "d1wse5.its.nv.gov",
        "d2wse1.its.nv.gov",
        "d2wse2.its.nv.gov",
        "d3wse1.its.nv.gov",
    },
    "louisiana": {
        "511la.org",
        "itsstreamingbr.dotd.la.gov",
        "itsstreamingbr2.dotd.la.gov",
        "itsstreamingno.dotd.la.gov",
    },
    "florida": {"fl511.com"},
    "georgia": {"511ga.org"},
    "northcarolina": {"drivenc.gov", "www.drivenc.gov"},
    "arizona": {"az511.gov"},
    "indiana": {"public.carsprogram.org", "skysfs4.trafficwise.org", "511in.org"},
    "us-published": {"gsccam.butlersheriff.org", "towercam.butlersheriff.org"},
    "newyork": {
        "511ny.org",
        "s7.nysdot.skyvdn.com",
        "s9.nysdot.skyvdn.com",
        "s51.nysdot.skyvdn.com",
        "s52.nysdot.skyvdn.com",
        "s53.nysdot.skyvdn.com",
    },
    "pennsylvania": {"www.511pa.com"},
    "newengland": {"newengland511.org"},
    "idaho": {"511.idaho.gov"},
    "connecticut": {"ctroads.org"},
    "alaska": {"511.alaska.gov"},
    "novascotia": {"511.novascotia.ca"},
    "newbrunswick": {"511.gnb.ca"},
    "saskatchewan": {"hotline.gov.sk.ca"},
    "newfoundland": {"511nl.ca"},
    "yukon": {"511yukon.ca"},
    "minnesota": {"public.carsprogram.org", "video.dot.state.mn.us"},
    "iowa": {"atmsqf.iowadot.gov"},
    "kansas": {"kscam.carsprogram.org", "www.kcscout.net"},
    "massachusetts": {"public.carsprogram.org"},
    "manitoba": {"www.manitoba511.ca"},
}


def media_url(value: Any, hosts: set[str] = MEDIA_HOSTS) -> str | None:
    """Only explicit public HTTPS origins. Never transfer untrusted HTML or credentials."""
    if not isinstance(value, str) or len(value) > 2048:
        return None
    try:
        p = urlsplit(value)
        if (
            p.scheme != "https"
            or p.hostname not in hosts
            or p.username
            or p.password
            or p.port not in (None, 443)
            or any(ord(c) < 33 for c in value)
        ):
            return None
    except ValueError:
        return None
    return value


def camera(
    provider: str,
    name: str,
    source: str,
    key: Any,
    title: Any,
    lat: Any,
    lon: Any,
    snapshot: Any = None,
    *,
    stream: Any = None,
    stream_type: str = "hls",
    external: Any = None,
    bounds: tuple[float, float, float, float] = (-90, 90, -180, 180),
) -> Camera | None:
    key = str(key)
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", key) or key == "None":
        return None
    try:
        latitude, longitude = float(lat), float(lon)
    except (TypeError, ValueError):
        return None
    if not (
        math.isfinite(latitude)
        and math.isfinite(longitude)
        and bounds[0] <= latitude <= bounds[1]
        and bounds[2] <= longitude <= bounds[3]
    ):
        return None
    hosts = PROVIDER_HOSTS.get(provider, set())
    image, video, link = (
        media_url(snapshot, hosts),
        media_url(stream, hosts),
        media_url(external, EXTERNAL_HOSTS),
    )
    if not image and not video and not link:
        return None
    # Only media types the provider actually publishes are admitted.
    if stream_type not in ("hls", "mp4"):
        video = None

    return Camera(
        id=f"{provider}:{key}",
        provider=provider,
        title=str(title or name).strip()[:240],
        latitude=latitude,
        longitude=longitude,
        snapshot_url=image,
        source_url=source,
        attribution=f"Source: {name}. Provider terms apply.",
        stream_url=video,
        stream_type=cast(Literal["hls", "mp4"], stream_type) if video else None,
        external_url=link,
    )


def unique(rows: list[Camera | None]) -> tuple[Camera, ...]:
    return tuple({c.id: c for c in rows if c is not None}.values())[:5000]
