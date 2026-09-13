"""Conservative catalogue coverage, separate from event geography.

Labels describe configured feed focus or registry jurisdiction, never publisher
nationality. Regional RSS focus follows docs/SOURCE_FEASIBILITY_2026_09.md;
instruments and registries follow their adapters' declared query coverage.
Unknown and operator-defined feeds deliberately remain unspecified.
"""

from dataclasses import dataclass
from typing import Literal

CoverageScope = Literal["global", "regional", "unspecified"]


@dataclass(frozen=True, slots=True)
class SourceCoverage:
    scope: CoverageScope = "unspecified"
    countries: tuple[str, ...] = ()
    regions: tuple[str, ...] = ()
    note: str = "Geographic coverage has not been catalogued."


GLOBAL = SourceCoverage(
    scope="global",
    note="International scope; coverage varies by query, reporting and provider availability.",
)
UNSPECIFIED = SourceCoverage()


def _focus(*countries: str, regions: tuple[str, ...] = ()) -> SourceCoverage:
    return SourceCoverage(
        "regional",
        countries,
        regions,
        "Configured reporting focus, not exclusive coverage or publisher nationality. "
        "Individual items may concern other places.",
    )


def _jurisdiction(country: str) -> SourceCoverage:
    return SourceCoverage(
        "regional",
        (country,),
        (),
        "Registry or public-record jurisdiction. Entities and subjects may be located elsewhere.",
    )


GLOBAL_IDS = frozenset(
    {
        "bbc_world",
        "dw_world",
        "france24_en",
        "aljazeera_en",
        "guardian_world",
        "lemonde_en",
        "un_news",
        "un_press",
        "reliefweb_updates",
        "crisis_group",
        "gov_uk_fcdo_news",
        "gov_uk_travel_advice",
        "us_state_travel_advisories",
        "usgs_earthquakes",
        "emsc_earthquakes",
        "nasa_eonet",
        "gdacs",
        "gvp_weekly",
        "firms_viirs_noaa20",
        "firms_public_noaa20",
        "firms_viirs_noaa21",
        "firms_public_noaa21",
        "adsb_global",
        "adsb_viewport",
        "ransomware_live",
        "ioda_outages",
        "cisa_kev",
        "who_don",
        "ifrc_go",
        "noaa_swpc_alerts",
        "noaa_swpc_scales",
        "swpc_kp",
        "celestrak_stations",
        "celestrak_active",
        "celestrak_military",
        "celestrak_skynet",
        "launch_library",
        "gdelt_events",
        "google_news_watchlists",
        "yt_bbc_news",
        "yt_reuters",
        "yt_dw_news",
        "yt_al_jazeera",
        "yt_france24",
        "yt_sky_news",
        "reddit_worldnews",
        "reddit_geopolitics",
        "aisstream",
        "research-openalex",
        "research-crossref",
        "research-world-bank",
        "economic-ecb",
        "economic_bbc_business",
        "economic_guardian_business",
        "economic_cgtn_business",
        "research-copernicus-footprints",
        "research-retained-area-feeds",
        "research-aiddata-projects",
        "research-gleif-profile",
        "research-gleif-direct-parent",
        "research-gleif-ultimate-parent",
        "research-designations-uksl",
        "research-designations-ofac_sdn",
    }
)

REGIONAL = {
    "economic_bank_england": _jurisdiction("GB"),
    "economic_hm_treasury": _jurisdiction("GB"),
    "economic_federal_reserve": _jurisdiction("US"),
    "economic_bank_russia": _jurisdiction("RU"),
    "economic_scmp_china": _focus("CN"),
    "economic_tehran_times": _focus("IR"),
    "meduza_en": _focus("RU"),
    "meduza_ru": _focus("RU"),
    "mediazona_ru": _focus("RU"),
    "insider_ru": _focus("RU"),
    "cdt_zh": _focus("CN"),
    "hrana_en": _focus("IR"),
    "hrana_fa": _focus("IR"),
    "iranwire_en": _focus("IR"),
    "iranwire_fa": _focus("IR"),
    "pravda_ua_en": _focus("UA"),
    "reddit_ukrainianconflict": _focus("UA", "RU"),
    "scmp_news": _focus("CN", "HK", regions=("Asia",)),
    "nikkei_asia": _focus(regions=("Asia",)),
    "times_of_israel": _focus("IL", regions=("Middle East",)),
    "dawn": _focus("PK"),
    "gov_uk_mod_news": _focus("GB"),
    "gov_uk_number_10": _focus("GB"),
    "gov_uk_home_office": _focus("GB"),
    "whitehouse_news": _focus("US"),
    "us_dod_news": _focus("US"),
    "cgtn_china": _focus("CN"),
    "russia_mfa_ru": _focus("RU"),
    "belta_ru": _focus("BY"),
    "interfax_ru": _focus("RU"),
    "ukrinform_en": _focus("UA"),
    "digitraffic_ais": SourceCoverage(
        "regional",
        ("FI",),
        ("Baltic Sea",),
        "Finnish coastal AIS receiver coverage, not global vessel coverage or flag nationality.",
    ),
    "barentswatch_ais": SourceCoverage(
        "regional",
        ("NO", "SJ"),
        ("Norwegian economic zone", "Svalbard protection zone", "Jan Mayen protection zone"),
        "Norwegian Coastal Administration open AIS maritime zones, not global vessel coverage "
        "or flag nationality. Small fishing and leisure/sailing vessels are excluded.",
    ),
    "nws_alerts": SourceCoverage(
        "regional",
        ("US",),
        (),
        "US National Weather Service alert coverage.",
    ),
    "nhc_atlantic": _focus(regions=("Atlantic Ocean",)),
    "nhc_east_pacific": _focus(regions=("Eastern Pacific Ocean",)),
    "jtwc": _focus(regions=("Western Pacific Ocean", "Indian Ocean", "Southern Hemisphere")),
    "research-uk-parliament": _jurisdiction("GB"),
    "research-contracts-finder": _jurisdiction("GB"),
    "research-companies-house": _jurisdiction("GB"),
    "research-companies-house-officers": _jurisdiction("GB"),
    "research-companies-house-psc": _jurisdiction("GB"),
    "research-sec-submissions": _jurisdiction("US"),
    "research-sec-company-directory": _jurisdiction("US"),
}


def source_coverage(source_id: str) -> SourceCoverage:
    """Derivatives inherit configured feed scope, never their language or edition."""
    for prefix in ("research_regional_", "research_social_", "research_publisher_"):
        if source_id.startswith(prefix):
            source_id = source_id.removeprefix(prefix)
            break
    # Search locale does not establish article geography.
    if source_id.startswith("research_google_news_"):
        return GLOBAL
    return GLOBAL if source_id in GLOBAL_IDS else REGIONAL.get(source_id, UNSPECIFIED)
