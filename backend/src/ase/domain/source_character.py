"""What kind of source a frozen item came from, as a readable table of feed identifiers.

The character of a source is a collection fact, not an assessment of its accuracy: a
national CERT advisory and a vendor blog are different kinds of reporting whatever
their Admiralty grades say. The table below is the only place these are assigned, so
an operator can read and extend it. An unlisted feed is left unclassified rather than
being guessed at.
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ase.domain.evidence import EvidenceItem


class SourceCharacter(StrEnum):
    OFFICIAL_ISSUER = "official_issuer"
    NATIONAL_CERT = "national_cert"
    SECURITY_VENDOR = "security_vendor"
    INSTRUMENT = "instrument"
    INDEPENDENT_OUTLET = "independent_outlet"
    SPECIALIST_OUTLET = "specialist_outlet"
    STATE_ALIGNED_OUTLET = "state_aligned_outlet"
    RESEARCH_BODY = "research_body"
    HUMANITARIAN_AGENCY = "humanitarian_agency"
    CRIMINAL_CLAIM = "criminal_claim"
    AGGREGATOR = "aggregator"
    SOCIAL_PLATFORM = "social_platform"
    UNCLASSIFIED = "unclassified"


CHARACTER_LABELS: dict[SourceCharacter, str] = {
    SourceCharacter.OFFICIAL_ISSUER: "an official issuer",
    SourceCharacter.NATIONAL_CERT: "a national CERT or government cyber authority",
    SourceCharacter.SECURITY_VENDOR: "a security vendor or research team advisory",
    SourceCharacter.INSTRUMENT: "instrument or sensor data",
    SourceCharacter.INDEPENDENT_OUTLET: "an independent news outlet",
    SourceCharacter.SPECIALIST_OUTLET: "a specialist outlet",
    SourceCharacter.STATE_ALIGNED_OUTLET: "a state-aligned outlet",
    SourceCharacter.RESEARCH_BODY: "a research or analysis body",
    SourceCharacter.HUMANITARIAN_AGENCY: "a humanitarian agency",
    SourceCharacter.CRIMINAL_CLAIM: "a criminal leak-site claim",
    SourceCharacter.AGGREGATOR: "an aggregator",
    SourceCharacter.SOCIAL_PLATFORM: "a social platform post",
    SourceCharacter.UNCLASSIFIED: "an unclassified feed",
}


def _row(*characters: SourceCharacter) -> frozenset[SourceCharacter]:
    return frozenset(characters)


_INSTRUMENT_ISSUER = _row(SourceCharacter.INSTRUMENT, SourceCharacter.OFFICIAL_ISSUER)
_OFFICIAL = _row(SourceCharacter.OFFICIAL_ISSUER)
_CERT = _row(SourceCharacter.NATIONAL_CERT, SourceCharacter.OFFICIAL_ISSUER)
_VENDOR = _row(SourceCharacter.SECURITY_VENDOR)
_OUTLET = _row(SourceCharacter.INDEPENDENT_OUTLET)
_SPECIALIST = _row(SourceCharacter.SPECIALIST_OUTLET)
_STATE = _row(SourceCharacter.STATE_ALIGNED_OUTLET)
_RESEARCH = _row(SourceCharacter.RESEARCH_BODY)
_RELIEF = _row(SourceCharacter.HUMANITARIAN_AGENCY)
_AGGREGATOR = _row(SourceCharacter.AGGREGATOR)


def _spread(
    ids: tuple[str, ...], characters: frozenset[SourceCharacter]
) -> dict[str, frozenset[SourceCharacter]]:
    return dict.fromkeys(ids, characters)


SOURCE_CHARACTERS: dict[str, frozenset[SourceCharacter]] = {
    **_spread(
        (
            "usgs_earthquakes",
            "emsc_earthquakes",
            "noaa_swpc_alerts",
            "noaa_swpc_scales",
            "swpc_kp",
            "nhc_atlantic",
            "nhc_east_pacific",
            "jtwc",
            "gvp_weekly",
            "ntwc_tsunami",
            "ptwc_tsunami",
            "nws_alerts",
            "celestrak_stations",
        ),
        _INSTRUMENT_ISSUER,
    ),
    **_spread(
        (
            "adsb_mil",
            "adsb_ladd",
            "adsb_pia",
            "adsb_emergency",
            "adsb_areas",
            "adsb_global",
            "ioda_outages",
            "ioda_outage_events",
            "cloudflare_radar_outages",
            "cloudflare_radar_attack_trends",
        ),
        _row(SourceCharacter.INSTRUMENT),
    ),
    **_spread(("gdacs", "nasa_eonet"), _AGGREGATOR | _OFFICIAL),
    **_spread(
        (
            "gov_uk_fcdo_news",
            "gov_uk_mod_news",
            "gov_uk_number_10",
            "gov_uk_home_office",
            "gov_uk_travel_advice",
            "whitehouse_news",
            "us_dod_news",
            "us_state_travel_advisories",
            "un_news",
            "un_press",
            "nga_navarea",
        ),
        _OFFICIAL,
    ),
    **_spread(("who_don", "ifrc_go", "reliefweb_updates"), _RELIEF | _OFFICIAL),
    **_spread(("crisis_group", "bellingcat", "isw_assessments", "ucdp_candidate"), _RESEARCH),
    **_spread(
        (
            "bbc_world",
            "dw_world",
            "france24_en",
            "aljazeera_en",
            "guardian_world",
            "lemonde_en",
            "scmp_news",
            "nikkei_asia",
            "times_of_israel",
            "anadolu_en",
            "dawn",
            "meduza_en",
            "kyiv_independent",
            "yt_bbc_news",
            "yt_reuters",
            "yt_dw_news",
            "yt_al_jazeera",
            "yt_france24",
            "yt_sky_news",
        ),
        _OUTLET,
    ),
    **_spread(("tass_en", "cgtn_china", "russia_mfa_ru", "pravda_ua_en"), _STATE),
    "ukraine_general_staff": _STATE | _OFFICIAL,
    **_spread(
        ("gdelt_events", "gdelt_news", "google_news_watchlists", "launch_library"), _AGGREGATOR
    ),
    "ransomware_live": _row(SourceCharacter.CRIMINAL_CLAIM) | _AGGREGATOR,
    "cisa_kev": _CERT,
    **_spread(
        (
            "cyber_ncsc_reports",
            "cyber_ncsc_news",
            "cyber_cert_eu",
            "cyber_acsc_advisories",
            "cyber_cisa_advisories",
            "cyber_cert_ua",
            "cyber_cccs_alerts",
            "cyber_cert_fr",
            "cyber_ic3_psa",
        ),
        _CERT,
    ),
    **_spread(
        (
            "cyber_microsoft_threat_intelligence",
            "cyber_cisco_talos",
            "cyber_google_threat_intelligence",
            "cyber_unit42",
        ),
        _VENDOR,
    ),
    **_spread(("cyber_the_record", "cyber_bleeping_computer"), _SPECIALIST),
    "cyber_sans_isc": _SPECIALIST | _RESEARCH,
}

_PREFIXES: tuple[tuple[str, frozenset[SourceCharacter]], ...] = (
    ("cyber_cert_", _CERT),
    ("cyber_ncsc", _CERT),
    ("telegram_", _row(SourceCharacter.SOCIAL_PLATFORM)),
    ("bluesky_", _row(SourceCharacter.SOCIAL_PLATFORM)),
    ("mastodon_", _row(SourceCharacter.SOCIAL_PLATFORM)),
    ("reddit_", _row(SourceCharacter.SOCIAL_PLATFORM)),
)


def characters_of(item: EvidenceItem) -> frozenset[SourceCharacter]:
    """The characters of one frozen item, from the table, then its declared provenance."""
    listed = SOURCE_CHARACTERS.get(item.source_id)
    if listed is not None:
        return listed
    for prefix, characters in _PREFIXES:
        if item.source_id.startswith(prefix):
            return characters
    if item.instrument:
        return _row(SourceCharacter.INSTRUMENT)
    role = item.source_rating.provenance_role if item.source_rating else "unassessed"
    if role == "platform":
        return _row(SourceCharacter.SOCIAL_PLATFORM)
    if role == "aggregator":
        return _AGGREGATOR
    return _row(SourceCharacter.UNCLASSIFIED)
