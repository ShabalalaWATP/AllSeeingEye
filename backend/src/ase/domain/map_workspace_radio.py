"""Radio artefacts store inputs, summaries and bounded terrain evidence, never raw events."""

from typing import Any

DRAFT_KEYS = {
    "values",
    "presetId",
    "propagation",
    "automaticHfMode",
    "radiusMode",
    "environment",
    "engineering",
    "study",
    "antenna",
}
VALUE_KEYS = {
    "distanceKm",
    "frequencyMHz",
    "transmitDbm",
    "transmitGainDbi",
    "receiveGainDbi",
    "lossesDb",
    "sensitivityDbm",
    "transmitHeightM",
    "receiveHeightM",
}
ENVIRONMENT_KEYS = {
    "radiusKm",
    "conductivitySm",
    "permittivity",
    "refractivity",
    "criticalFrequencyMHz",
    "virtualHeightKm",
    "minElevationDeg",
    "maxElevationDeg",
}
ENGINEERING_KEYS = {"reserveDb", "obstacleHeightM", "earthFactor"}
RESULT_KEYS = {
    "kind",
    "status",
    "distanceKm",
    "receivedDbm",
    "marginDb",
    "sampleCount",
    "missingSamples",
}
PROVENANCE_KEYS = {"model", "limitations", "terrainAttribution", "terrainSourceUrl"}


def _record(value: object, keys: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) - keys:
        raise ValueError("Unsupported radio study fields.")
    return value


def _flat(value: object, keys: set[str], *, text_only: bool = False) -> None:
    record = _record(value, keys)
    for item in record.values():
        if isinstance(item, (dict, list)) or (text_only and not isinstance(item, str)):
            raise ValueError("Radio study fields must be scalar values.")
        if isinstance(item, str) and len(item) > (100 if text_only else 6000):
            raise ValueError("Radio study field is too long.")


def validate_radio(payload: dict[str, Any]) -> None:
    allowed = {
        "schemaVersion",
        "savedAt",
        "draft",
        "origin",
        "receiver",
        "siteNames",
        "result",
        "provenance",
        "terrainEvidence",
    }
    _record(payload, allowed)
    if type(payload.get("schemaVersion")) is not int or payload["schemaVersion"] != 1:
        raise ValueError("Unsupported radio study document.")
    _draft(payload.get("draft"))
    for key in ("origin", "receiver"):
        point = payload.get(key)
        if point is not None and (
            not isinstance(point, list)
            or len(point) != 2
            or any(type(item) not in (int, float) for item in point)
            or not -180 <= point[0] <= 180
            or not -90 <= point[1] <= 90
        ):
            raise ValueError("Invalid radio site coordinates.")
    if "savedAt" in payload and (
        not isinstance(payload["savedAt"], str) or len(payload["savedAt"]) > 40
    ):
        raise ValueError("Invalid radio saved timestamp.")
    if "siteNames" in payload:
        _flat(payload["siteNames"], {"origin", "receiver"}, text_only=True)
    if payload.get("result") is not None:
        _flat(payload["result"], RESULT_KEYS)
    if "provenance" in payload:
        _flat(payload["provenance"], PROVENANCE_KEYS)
    if payload.get("terrainEvidence") is not None:
        _terrain(payload["terrainEvidence"])


def _terrain(value: object) -> None:
    terrain = _record(value, {"zoom", "resolutionM", "samples", "profiles"})
    zoom, resolution = terrain.get("zoom"), terrain.get("resolutionM")
    if (
        type(zoom) is not int
        or not 0 <= zoom <= 22
        or not isinstance(resolution, (int, float))
        or isinstance(resolution, bool)
        or not 0 < resolution <= 100000
    ):
        raise ValueError("Invalid terrain resolution.")
    samples = terrain.get("samples")
    profiles = terrain.get("profiles")
    if not isinstance(samples, list) or len(samples) > 1000:
        raise ValueError("Terrain evidence supports up to 1000 samples.")
    if not isinstance(profiles, list) or len(profiles) > 24:
        raise ValueError("Terrain evidence supports up to 24 profiles.")
    for point in samples:
        if (
            not isinstance(point, list)
            or len(point) != 3
            or any(type(item) not in (int, float) for item in point[:2])
            or not -180 <= point[0] <= 180
            or not -90 <= point[1] <= 90
            or (
                point[2] is not None
                and (type(point[2]) not in (int, float) or not -12000 <= point[2] <= 10000)
            )
        ):
            raise ValueError("Invalid terrain sample.")
    for item in profiles:
        profile = _record(item, {"bearingDegrees", "indices", "distancesM"})
        bearing = profile.get("bearingDegrees")
        if (
            not isinstance(bearing, (int, float))
            or isinstance(bearing, bool)
            or not -360 <= bearing <= 360
        ):
            raise ValueError("Invalid terrain profile bearing.")
        indices, distances = profile.get("indices"), profile.get("distancesM")
        if (
            not isinstance(indices, list)
            or not isinstance(distances, list)
            or len(indices) != len(distances)
            or any(type(index) is not int or not 0 <= index < len(samples) for index in indices)
            or any(
                type(distance) not in (int, float) or not 0 <= distance <= 2000000
                for distance in distances
            )
        ):
            raise ValueError("Invalid terrain profile samples.")


def _draft(raw: object) -> None:
    draft = _record(raw, DRAFT_KEYS)
    for key, keys in (
        ("values", VALUE_KEYS),
        ("environment", ENVIRONMENT_KEYS),
        ("engineering", ENGINEERING_KEYS),
    ):
        if key in draft:
            _flat(draft[key], keys, text_only=True)
    for key, value in draft.items():
        if key not in {"values", "environment", "engineering", "antenna"} and (
            not isinstance(value, str) or len(value) > 100
        ):
            raise ValueError("Invalid radio form value.")
    if "antenna" in draft:
        antenna = _record(
            draft["antenna"],
            {"enabled", "transmitterBearing", "receiverBearing", "beamwidth", "maximumAttenuation"},
        )
        if type(antenna.get("enabled")) is not bool:
            raise ValueError("Invalid antenna enabled setting.")
        _flat(
            {key: value for key, value in antenna.items() if key != "enabled"},
            {"transmitterBearing", "receiverBearing", "beamwidth", "maximumAttenuation"},
            text_only=True,
        )
