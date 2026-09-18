"""World regions as sets of the countries this application already knows.

A region is a collection choice, not a geography: choosing Europe asks for evidence
attributed to any of these countries, exactly as naming each one would, without the
eight-country limit that bounds provider fan-out. The Middle East overlaps Asia and
Africa on purpose, because that is how the reporting names it. Codes are ISO 3166
alpha-2 as packaged with the Natural Earth outlines, plus the user-assigned codes
those outlines carry for Kosovo, Northern Cyprus and Somaliland.
"""

from __future__ import annotations

from enum import StrEnum
from types import MappingProxyType

MAX_REGIONS = 8


class Region(StrEnum):
    AFRICA = "africa"
    ASIA = "asia"
    EUROPE = "europe"
    MIDDLE_EAST = "middle_east"
    NORTH_AMERICA = "north_america"
    SOUTH_AMERICA = "south_america"
    OCEANIA = "oceania"
    ANTARCTICA = "antarctica"


REGION_LABELS: MappingProxyType[Region, str] = MappingProxyType(
    {
        Region.AFRICA: "Africa",
        Region.ASIA: "Asia",
        Region.EUROPE: "Europe",
        Region.MIDDLE_EAST: "Middle East",
        Region.NORTH_AMERICA: "North America",
        Region.SOUTH_AMERICA: "South America",
        Region.OCEANIA: "Oceania",
        Region.ANTARCTICA: "Antarctica",
    }
)

_AFRICA = (
    "AO BF BI BJ BW CD CF CG CI CM DJ DZ EG EH ER ET GA GH GM GN GQ GW KE LR LS LY MA MG ML "
    "MR MW MZ NA NE NG RW SD SL SN SO SS SZ TD TF TG TN TZ UG XS ZA ZM ZW"
)
_ASIA = (
    "AE AF AM AZ BD BN BT CN CY GE ID IL IN IQ IR JO JP KG KH KP KR KW KZ LA LB LK MM MN MY "
    "NP OM PH PK PS QA SA SY TH TJ TL TM TR TW UZ VN XN YE"
)
_EUROPE = (
    "AL AT BA BE BG BY CH CZ DE DK EE ES FI FR GB GR HR HU IE IS IT LT LU LV MD ME MK NL NO "
    "PL PT RO RS RU SE SI SK UA XK"
)
_MIDDLE_EAST = "AE EG IL IQ IR JO KW LB OM PS QA SA SY TR YE"
_NORTH_AMERICA = "BS BZ CA CR CU DO GL GT HN HT JM MX NI PA PR SV TT US"
_SOUTH_AMERICA = "AR BO BR CL CO EC FK GY PE PY SR UY VE"
_OCEANIA = "AU FJ NC NZ PG SB VU"
_ANTARCTICA = "AQ"

REGION_COUNTRIES: MappingProxyType[Region, frozenset[str]] = MappingProxyType(
    {
        Region.AFRICA: frozenset(_AFRICA.split()),
        Region.ASIA: frozenset(_ASIA.split()),
        Region.EUROPE: frozenset(_EUROPE.split()),
        Region.MIDDLE_EAST: frozenset(_MIDDLE_EAST.split()),
        Region.NORTH_AMERICA: frozenset(_NORTH_AMERICA.split()),
        Region.SOUTH_AMERICA: frozenset(_SOUTH_AMERICA.split()),
        Region.OCEANIA: frozenset(_OCEANIA.split()),
        Region.ANTARCTICA: frozenset(_ANTARCTICA.split()),
    }
)


def normalise_regions(values: object) -> tuple[Region, ...]:
    """Known regions, deduplicated, in the order given; anything else is refused."""
    if not isinstance(values, list | tuple):
        raise ValueError("Regions must be a list")
    seen: dict[Region, None] = {}
    for value in values:
        try:
            seen.setdefault(Region(str(value).strip().lower()), None)
        except ValueError:
            raise ValueError("Unknown region") from None
    if len(seen) > MAX_REGIONS:
        raise ValueError(f"Choose up to {MAX_REGIONS} regions")
    return tuple(seen)


def region_countries(regions: tuple[Region, ...] | tuple[str, ...]) -> tuple[str, ...]:
    """Every country in the chosen regions, in a stable order for frozen scopes."""
    return tuple(
        sorted({iso for region in regions for iso in REGION_COUNTRIES[Region(str(region))]})
    )
