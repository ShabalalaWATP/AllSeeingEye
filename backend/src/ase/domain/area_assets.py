"""The one reviewed table that decides when a map register or spatial instrument is eligible.

Read this file as a register. A lookup is a collection choice about a place: it never
establishes that anything happened there, and a packaged record of a site is never
evidence of that site's current state.

Restraint is the point. Vague topical overlap is not a trigger. A question about an
election, a court ruling, a sanctions designation, a cyber advisory naming no place,
a central bank decision or a market move must not pull in map data. Only the phrases
below, matched on whole words, make a class eligible, and the caller must also hold a
geography it can resolve from packaged data (or a directly drawn area, which is itself
a request about the ground inside it).
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

TRIGGER_POLICY_VERSION = "ase-area-asset-triggers-v1"
MAX_MATCHED_PHRASES = 6
MAX_TRIGGER_TEXT = 8_000


class AssetClass(StrEnum):
    """Packaged registers whose geometry this application already holds."""

    DATA_CENTRES = "data_centres"
    ENERGY_SITES = "energy_sites"
    NUCLEAR_FACILITIES = "nuclear_facilities"
    SEMICONDUCTOR_SITES = "semiconductor_sites"
    SUBMARINE_CABLES = "submarine_cables"
    GROUND_STATIONS = "ground_stations"
    CAMERAS = "cameras"


class InstrumentClass(StrEnum):
    """Spatial observations the application already collects, filtered to a geography."""

    THERMAL_DETECTIONS = "thermal_detections"
    GNSS_INTERFERENCE = "gnss_interference"
    AIRCRAFT_ACTIVITY = "aircraft_activity"
    VESSEL_ACTIVITY = "vessel_activity"


# Reviewed 2026-09-17. Asset nouns first, then the physical effects for which that
# asset class is the subject rather than incidental background.
_ASSET_PHRASES: dict[AssetClass, tuple[str, ...]] = {
    AssetClass.DATA_CENTRES: (
        "data centre",
        "data centres",
        "data center",
        "data centers",
        "datacentre",
        "datacentres",
        "datacenter",
        "datacenters",
        "colocation",
        "co-location",
        "server farm",
        "server farms",
        "hyperscale",
        "cloud region",
        "cloud regions",
        "availability zone",
        "availability zones",
    ),
    AssetClass.ENERGY_SITES: (
        "power station",
        "power stations",
        "power plant",
        "power plants",
        "powerplant",
        "substation",
        "substations",
        "power grid",
        "electricity grid",
        "national grid",
        "refinery",
        "refineries",
        "oil terminal",
        "oil terminals",
        "lng terminal",
        "lng terminals",
        "gas terminal",
        "gas terminals",
        "pipeline",
        "pipelines",
        "transmission line",
        "transmission lines",
        "hydroelectric",
        "wind farm",
        "wind farms",
        "solar farm",
        "solar farms",
        "blackout",
        "blackouts",
        "power cut",
        "power cuts",
        "load shedding",
        "power outage",
        "power outages",
        "electricity supply",
        "energy infrastructure",
    ),
    AssetClass.NUCLEAR_FACILITIES: (
        "nuclear",
        "reactor",
        "reactors",
        "enrichment",
        "atomic energy",
    ),
    AssetClass.SEMICONDUCTOR_SITES: (
        "semiconductor",
        "semiconductors",
        "chip fab",
        "chip fabs",
        "chipmaker",
        "chipmakers",
        "wafer",
        "wafers",
        "foundry",
        "foundries",
        "fabrication plant",
        "fabrication plants",
    ),
    AssetClass.SUBMARINE_CABLES: (
        "submarine cable",
        "submarine cables",
        "subsea cable",
        "subsea cables",
        "undersea cable",
        "undersea cables",
        "sea cable",
        "sea cables",
        "cable landing",
        "landing station",
        "landing stations",
        "fibre-optic cable",
        "fibre optic cable",
        "fiber-optic cable",
        "fiber optic cable",
        "internet backbone",
        "cable cut",
        "cable cuts",
        "cable damage",
        "connectivity loss",
    ),
    AssetClass.GROUND_STATIONS: (
        "ground station",
        "ground stations",
        "teleport",
        "teleports",
        "earth station",
        "earth stations",
        "satellite uplink",
        "satellite gateway",
        "downlink",
    ),
    AssetClass.CAMERAS: (
        "cctv",
        "traffic camera",
        "traffic cameras",
        "webcam",
        "webcams",
        "public camera",
        "public cameras",
        "live camera",
        "live cameras",
        "street camera",
        "street cameras",
    ),
}

# Instrument sweeps spend a metered request or read a bounded live aggregate, so their
# vocabulary is deliberately narrower than the asset registers. Bare "fire" is excluded
# because "ceasefire", "came under fire" and "firefight" are not thermal observations;
# bare "spoofing" is excluded because it is ordinary cyber vocabulary.
_INSTRUMENT_PHRASES: dict[InstrumentClass, tuple[str, ...]] = {
    InstrumentClass.THERMAL_DETECTIONS: (
        "wildfire",
        "wildfires",
        "bushfire",
        "bushfires",
        "forest fire",
        "forest fires",
        "active fire",
        "active fires",
        "fire detection",
        "fire detections",
        "thermal anomaly",
        "thermal anomalies",
        "thermal detection",
        "thermal detections",
        "burning",
        "blaze",
        "arson",
        "smoke plume",
        "smoke plumes",
        "gas flare",
        "gas flaring",
        "flaring",
    ),
    InstrumentClass.GNSS_INTERFERENCE: (
        "gnss",
        "gps jamming",
        "gps spoofing",
        "gps interference",
        "gnss jamming",
        "gnss spoofing",
        "gnss interference",
        "signal jamming",
        "signal spoofing",
        "jamming",
        "navigation interference",
        "satellite navigation",
        "ais spoofing",
    ),
    InstrumentClass.AIRCRAFT_ACTIVITY: (
        "flight activity",
        "air activity",
        "air traffic",
        "military aircraft",
        "military flight",
        "military flights",
        "transport aircraft",
        "aerial reconnaissance",
        "reconnaissance flight",
        "reconnaissance flights",
        "surveillance flight",
        "surveillance flights",
        "airspace closure",
        "airspace closures",
        "tanker aircraft",
        "air bridge",
    ),
    InstrumentClass.VESSEL_ACTIVITY: (
        "ship activity",
        "shipping activity",
        "vessel activity",
        "vessel movement",
        "vessel movements",
        "ship movement",
        "ship movements",
        "shadow fleet",
        "dark fleet",
        "naval activity",
        "naval movement",
        "naval movements",
        "port call",
        "port calls",
        "anchorage",
        "maritime traffic",
    ),
}

ASSET_PHRASES = MappingProxyType(dict(_ASSET_PHRASES))
INSTRUMENT_PHRASES = MappingProxyType(dict(_INSTRUMENT_PHRASES))


def _pattern(phrases: tuple[str, ...]) -> re.Pattern[str]:
    ordered = sorted(phrases, key=len, reverse=True)
    return re.compile(r"\b(?:" + "|".join(re.escape(row) for row in ordered) + r")\b")


_ASSET_PATTERNS = MappingProxyType(
    {key.value: _pattern(value) for key, value in _ASSET_PHRASES.items()}
)
_INSTRUMENT_PATTERNS = MappingProxyType(
    {key.value: _pattern(value) for key, value in _INSTRUMENT_PHRASES.items()}
)


@dataclass(frozen=True, slots=True)
class TriggerMatch:
    """One eligible class and the reviewed phrases that made it eligible."""

    name: str
    phrases: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.name or not self.phrases or len(self.phrases) > MAX_MATCHED_PHRASES:
            raise ValueError("A trigger match needs a class and one to six matched phrases")

    def describe(self) -> str:
        return f"{self.name} ({', '.join(self.phrases)})"


def _match(patterns: Mapping[str, re.Pattern[str]], text: str) -> tuple[TriggerMatch, ...]:
    folded = text.casefold()[:MAX_TRIGGER_TEXT]
    result = []
    for key, pattern in patterns.items():
        found = tuple(dict.fromkeys(pattern.findall(folded)))[:MAX_MATCHED_PHRASES]
        if found:
            result.append(TriggerMatch(key, found))
    return tuple(result)


def asset_triggers(text: str) -> tuple[TriggerMatch, ...]:
    """Reviewed asset classes named by this text, in register order."""
    return _match(_ASSET_PATTERNS, text)


def instrument_triggers(text: str) -> tuple[TriggerMatch, ...]:
    """Reviewed spatial instrument classes named by this text, in register order."""
    return _match(_INSTRUMENT_PATTERNS, text)


def trigger_text(*parts: str | None) -> str:
    """One bounded haystack from the question, the operator terms and the requirements."""
    return " ".join(part for part in parts if part)[:MAX_TRIGGER_TEXT]


NO_TRIGGER_REASON = (
    "No reviewed asset or physical-effect phrase appears in the question, the operator's "
    "search terms or the intelligence requirements, so no packaged register or spatial "
    "instrument was read. Topical overlap alone is not a reason to attach map data."
)
