"""The map features a question can name, and how OpenStreetMap tags each of them.

Bellingcat's osm-search turns "a church near a railway and a river" into places on the map.
Here the vocabulary is fixed and small: a question or its search terms select feature
classes by plain words, and each class maps to the exact OpenStreetMap tag filters that
find it. Nothing is guessed from free text beyond this table, so a research query can
never ask the map for arbitrary tags.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

MAX_CLASSES = 6


@dataclass(frozen=True, slots=True)
class FeatureClass:
    key: str
    label: str
    words: tuple[str, ...]
    #: Overpass tag filters, each applied to nodes, ways and relations together.
    filters: tuple[str, ...]


def _c(key: str, label: str, words: str, *filters: str) -> FeatureClass:
    return FeatureClass(key, label, tuple(words.split("|")), filters)


FEATURE_CLASSES: tuple[FeatureClass, ...] = (
    _c(
        "church",
        "Church",
        "church|cathedral|chapel|basilica",
        '["amenity"="place_of_worship"]["religion"="christian"]',
    ),
    _c("mosque", "Mosque", "mosque|minaret", '["amenity"="place_of_worship"]["religion"="muslim"]'),
    _c(
        "synagogue", "Synagogue", "synagogue", '["amenity"="place_of_worship"]["religion"="jewish"]'
    ),
    _c(
        "temple",
        "Temple",
        "temple|pagoda|shrine",
        '["amenity"="place_of_worship"]["religion"~"buddhist|hindu|shinto|taoist|sikh"]',
    ),
    _c(
        "railway_station",
        "Railway station",
        "railway station|train station|station platform|rail station",
        '["railway"="station"]',
    ),
    _c(
        "bridge",
        "Bridge",
        "bridge|viaduct|overpass",
        '["man_made"="bridge"]',
        '["bridge"="yes"]["highway"~"primary|secondary|trunk|motorway"]',
    ),
    _c("stadium", "Stadium", "stadium|arena|sports ground", '["leisure"="stadium"]'),
    _c(
        "airport",
        "Airport or airfield",
        "airport|airfield|aerodrome|runway|air base|airbase",
        '["aeroway"="aerodrome"]',
    ),
    _c("helipad", "Helipad", "helipad|heliport", '["aeroway"~"helipad|heliport"]'),
    _c(
        "port",
        "Port or harbour",
        "port|harbour|harbor|dock|wharf|quay|marina",
        '["harbour"="yes"]',
        '["landuse"="harbour"]',
        '["industrial"="port"]',
        '["leisure"="marina"]',
    ),
    _c(
        "power_plant",
        "Power plant",
        "power plant|power station|generating station|nuclear plant|reactor",
        '["power"="plant"]',
    ),
    _c(
        "substation",
        "Electrical substation",
        "substation|transformer station",
        '["power"="substation"]',
    ),
    _c(
        "wind_farm",
        "Wind turbines",
        "wind turbine|wind farm|windmill",
        '["power"="generator"]["generator:source"="wind"]',
    ),
    _c(
        "solar_farm",
        "Solar farm",
        "solar farm|solar plant|solar panels",
        '["power"="plant"]["plant:source"="solar"]',
    ),
    _c("dam", "Dam", "dam|reservoir wall|spillway", '["waterway"="dam"]'),
    _c(
        "hospital",
        "Hospital",
        "hospital|clinic|medical centre|medical center",
        '["amenity"="hospital"]',
    ),
    _c(
        "school",
        "School or university",
        "school|university|college|campus",
        '["amenity"~"school|university|college"]',
    ),
    _c(
        "tower",
        "Tower or mast",
        "tower|mast|antenna|pylon|radar",
        '["man_made"~"tower|mast|communications_tower"]',
    ),
    _c("water_tower", "Water tower", "water tower", '["man_made"="water_tower"]'),
    _c("lighthouse", "Lighthouse", "lighthouse", '["man_made"="lighthouse"]'),
    _c(
        "chimney",
        "Industrial chimney",
        "chimney|smokestack|cooling tower",
        '["man_made"~"chimney|cooling_tower"]',
    ),
    _c(
        "fuel",
        "Fuel station",
        "fuel station|petrol station|gas station|filling station",
        '["amenity"="fuel"]',
    ),
    _c(
        "cemetery",
        "Cemetery",
        "cemetery|graveyard|burial ground",
        '["landuse"="cemetery"]',
        '["amenity"="grave_yard"]',
    ),
    _c(
        "monument",
        "Monument or memorial",
        "monument|memorial|statue|obelisk",
        '["historic"~"monument|memorial"]',
    ),
    _c(
        "castle",
        "Castle or fort",
        "castle|fortress|fort|citadel",
        '["historic"~"castle|fort|citadel"]',
    ),
    _c(
        "factory",
        "Factory or works",
        "factory|plant|works|refinery|steelworks|shipyard",
        '["man_made"="works"]',
        '["industrial"~"refinery|shipyard|factory"]',
    ),
    _c(
        "mine",
        "Mine or quarry",
        "mine|quarry|pit|colliery",
        '["landuse"="quarry"]',
        '["man_made"~"mineshaft|adit"]',
    ),
    _c(
        "prison",
        "Prison",
        "prison|jail|detention centre|detention center|penal colony",
        '["amenity"="prison"]',
    ),
    _c(
        "military",
        "Military site",
        "military base|barracks|garrison|military airfield|training ground|army base|naval base",
        '["landuse"="military"]',
        '["military"]',
    ),
    _c("river", "River", "river|riverbank|estuary", '["waterway"="river"]'),
    _c(
        "lake",
        "Lake or reservoir",
        "lake|reservoir|lagoon",
        '["natural"="water"]["water"~"lake|reservoir|lagoon"]',
    ),
    _c("roundabout", "Roundabout", "roundabout|traffic circle", '["junction"="roundabout"]'),
    _c("market", "Market", "market|bazaar|souk", '["amenity"="marketplace"]'),
    _c("hotel", "Hotel", "hotel|resort", '["tourism"~"hotel|resort"]'),
    _c(
        "embassy",
        "Embassy or consulate",
        "embassy|consulate|diplomatic mission",
        '["office"="diplomatic"]',
    ),
    _c(
        "border",
        "Border crossing",
        "border crossing|checkpoint|border post|customs post",
        '["barrier"="border_control"]',
    ),
    _c(
        "bus_station",
        "Bus station",
        "bus station|bus terminal|coach station",
        '["amenity"="bus_station"]',
    ),
    _c(
        "government",
        "Government building",
        "parliament|ministry|town hall|city hall|government building|presidential palace|palace",
        '["office"="government"]',
        '["amenity"="townhall"]',
        '["historic"="palace"]',
    ),
    _c("police", "Police station", "police station|police headquarters", '["amenity"="police"]'),
    _c("fire_station", "Fire station", "fire station|firehouse", '["amenity"="fire_station"]'),
    _c("silo", "Silo or grain store", "silo|grain elevator|grain store", '["man_made"="silo"]'),
    _c("museum", "Museum", "museum|gallery", '["tourism"="museum"]'),
    _c(
        "theatre",
        "Theatre or cinema",
        "theatre|theater|opera house|cinema",
        '["amenity"~"theatre|cinema"]',
    ),
    _c("pier", "Pier or jetty", "pier|jetty|breakwater", '["man_made"~"pier|breakwater"]'),
)

_BY_KEY = {feature.key: feature for feature in FEATURE_CLASSES}
_PATTERNS = tuple(
    (
        feature,
        re.compile(
            r"(?<![\w-])(?:"
            + "|".join(re.escape(word) for word in feature.words)
            + r")(?:s|es)?(?![\w-])",
            re.I,
        ),
    )
    for feature in FEATURE_CLASSES
)


def feature_class(key: str) -> FeatureClass | None:
    return _BY_KEY.get(key)


def classes_for(text: str, *, limit: int = MAX_CLASSES) -> tuple[FeatureClass, ...]:
    """The feature classes a question names, in table order, at most ``limit`` of them."""
    sample = text[:4000]
    found = [feature for feature, pattern in _PATTERNS if pattern.search(sample)]
    return tuple(found[:limit])
