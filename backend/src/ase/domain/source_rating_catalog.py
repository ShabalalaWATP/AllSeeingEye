"""Explicit inherited registry assignments, described without claiming measured accuracy."""

from dataclasses import dataclass
from typing import Literal

ProvenanceRole = Literal["originator", "publisher", "aggregator", "platform", "unassessed"]


@dataclass(frozen=True, slots=True)
class RatingEntry:
    grade: str
    basis: str
    scope: str
    role: ProvenanceRole
    limitations: tuple[str, ...]


def _entries(
    grades: dict[str, str],
    basis: str,
    scope: str,
    role: ProvenanceRole,
    *limitations: str,
) -> dict[str, RatingEntry]:
    return {
        id_: RatingEntry(grade, basis, scope, role, limitations) for id_, grade in grades.items()
    }


CATALOGUE = {
    **_entries(
        {"usgs_earthquakes": "A", "emsc_earthquakes": "A"},
        "Inherited editorial assignment for a specialist seismic event catalogue with "
        "structured event identifiers, times and measurements.",
        "Published earthquake catalogue solutions and their reported parameters.",
        "originator",
        "Initial locations and magnitudes can change; catalogue coverage is not complete "
        "and the feed does not independently establish casualties or damage.",
    ),
    **_entries(
        {"gdacs": "A", "nasa_eonet": "A"},
        "Inherited editorial assignment for structured hazard aggregation and published "
        "event products, not a reliability assessment of each upstream contributor.",
        "The service's hazard catalogue, alert or event product.",
        "aggregator",
        "Several services can reuse the same underlying observations. Modelled severity, "
        "classification and reported geometry need item-level interpretation.",
    ),
    **_entries(
        {"noaa_swpc_alerts": "A", "noaa_swpc_scales": "A", "swpc_kp": "A"},
        "Inherited editorial assignment for the issuing specialist space-weather service's "
        "structured observations, indices and notices.",
        "Published space-weather indices, scales and alerts.",
        "originator",
        "Observed indices and forecasts differ. Issue time, revisions and regional impacts "
        "must not be inferred from a global index alone.",
    ),
    **_entries(
        {"nhc_atlantic": "A", "nhc_east_pacific": "A", "jtwc": "A"},
        "Inherited editorial assignment for an issuing cyclone warning centre's "
        "structured advisory products.",
        "Cyclone advisories within the centre's covered basins and issue periods.",
        "originator",
        "Forecast tracks and intensity are estimates, not verified future outcomes. "
        "Different centres can use different conventions and shared observations.",
    ),
    **_entries(
        {"gvp_weekly": "A", "ntwc_tsunami": "A", "ptwc_tsunami": "A", "nws_alerts": "A"},
        "Inherited editorial assignment for a specialist institution's published "
        "hazard reports or warning products.",
        "The issuing body's volcanic, tsunami or weather notices and stated coverage.",
        "originator",
        "Warnings describe assessed hazards; absence of a warning is not proof of safety. "
        "Weekly reports, observations and predictions have different time scopes.",
    ),
    **_entries(
        {
            "adsb_mil": "B",
            "adsb_ladd": "B",
            "adsb_pia": "B",
            "adsb_emergency": "A",
            "adsb_areas": "B",
            "adsb_global": "B",
        },
        "Inherited feed-specific editorial assignment for community receiver observations "
        "and associated aircraft database classifications.",
        "Received ADS-B positions, broadcast codes and the service's aircraft labels.",
        "aggregator",
        "Receiver coverage, stale positions, spoofing and classification errors are possible. "
        "Privacy or military labels do not establish intent; a squawk alone does not "
        "verify an incident.",
    ),
    **_entries(
        {"cisa_kev": "A"},
        "Inherited editorial assignment for the issuing authority's named vulnerability catalogue.",
        "Catalogue inclusion and the authority's published vulnerability information.",
        "originator",
        "Catalogue inclusion does not establish exploitation on an operator's own systems; "
        "absence does not establish that a vulnerability is unexploited.",
    ),
    **_entries(
        {"who_don": "A", "ifrc_go": "B"},
        "Inherited editorial assignment for attributed public-health or humanitarian "
        "institutional reporting.",
        "Published outbreak notices, field reports and response records.",
        "originator",
        "Reports can rely on national or field reporting with delays and incomplete coverage. "
        "Institutional publication does not independently verify every underlying claim.",
    ),
    **_entries(
        {"nga_navarea": "A"},
        "Inherited editorial assignment for published maritime safety warnings from "
        "the registered issuing service.",
        "NAVAREA warning text, stated areas and issue periods.",
        "originator",
        "Warnings are safety notices, not a complete maritime activity record. "
        "Cancellation, expiry and geographic precision require the original notice.",
    ),
    **_entries(
        {"celestrak_stations": "A", "launch_library": "B"},
        "Inherited editorial assignment for structured space-object or launch catalogue records.",
        "Published orbital elements or launch schedules, with their stated epochs and status.",
        "aggregator",
        "Propagated satellite positions are model estimates, not fresh observations. "
        "Launch schedules can change and catalogue services can share upstream sources.",
    ),
    **_entries(
        {"ransomware_live": "B"},
        "Inherited editorial assignment for collection of attributed ransomware reporting, "
        "not acceptance of extortion actors' claims.",
        "Reported victim listings and the collection service's associated metadata.",
        "aggregator",
        "Criminal claims can be exaggerated, false or duplicated. Listing a victim does not "
        "independently establish compromise, attribution or impact.",
    ),
    **_entries(
        {"ioda_outages": "B", "ioda_outage_events": "B"},
        "Inherited editorial assignment for a specialist service's combined network observations.",
        "Published connectivity measurements and outage signals.",
        "aggregator",
        "Measurement coverage and thresholds affect detection. A connectivity signal alone "
        "does not establish deliberate interference or its cause.",
    ),
    **_entries(
        {"cloudflare_radar_outages": "B"},
        "Inherited editorial assignment for Cloudflare Radar outage annotations.",
        "Provider-reported disruption timing and geographic scope.",
        "aggregator",
        "Radar coverage and classification are provider assessments. Country scope is not "
        "a precise incident location, and an annotation alone does not establish cause.",
    ),
    **_entries(
        {"cloudflare_radar_attack_trends": "B"},
        "Inherited editorial assignment for Cloudflare Radar aggregated attack measurements.",
        "Ranked share of Cloudflare-observed mitigated traffic by attacked zone billing country.",
        "aggregator",
        "A country share is not an incident count, attacker location, or representative rate "
        "for all networks in that country.",
    ),
    **_entries(
        {
            "gov_uk_fcdo_news": "B",
            "gov_uk_mod_news": "B",
            "gov_uk_number_10": "B",
            "gov_uk_home_office": "B",
            "whitehouse_news": "B",
            "us_dod_news": "B",
            "gov_uk_travel_advice": "A",
            "us_state_travel_advisories": "A",
            "un_news": "B",
            "un_press": "B",
        },
        "Inherited editorial assignment for attributable publication by the named institution.",
        "The institution's own statements, advice or reporting within its stated remit.",
        "originator",
        "Reliable attribution is distinct from truth of every statement. Institutions can "
        "be interested parties; advice reflects the issuing body's perspective and remit.",
    ),
    **_entries(
        {"reliefweb_updates": "B"},
        "Inherited editorial assignment for an attributed humanitarian document index, "
        "not a common reliability grade for every republished author.",
        "Index metadata and links to the original humanitarian reports.",
        "aggregator",
        "Original publishers retain responsibility for their reports. Republication does "
        "not add independent corroboration or establish the original author's reliability.",
    ),
    **_entries(
        {"crisis_group": "B"},
        "Inherited editorial assignment for attributable specialist conflict analysis.",
        "The organisation's published analysis and cited reporting.",
        "publisher",
        "Analysis is interpretation, not direct observation. Underlying citations, "
        "assumptions and geographic coverage still require examination.",
    ),
    **_entries(
        {
            "bbc_world": "B",
            "dw_world": "B",
            "france24_en": "B",
            "aljazeera_en": "B",
            "guardian_world": "C",
            "lemonde_en": "C",
            "scmp_news": "C",
            "nikkei_asia": "C",
            "times_of_israel": "C",
            "anadolu_en": "C",
            "dawn": "C",
            "meduza_en": "C",
            "pravda_ua_en": "C",
            "kyiv_independent": "C",
            "bellingcat": "B",
        },
        "Inherited B/C editorial assignment for this named outlet in the registry; "
        "the registry distinguishes publisher categories but records no measured track record.",
        "The named publisher's reporting supplied through this particular feed.",
        "publisher",
        "Bylines, quotations, wire reuse, corrections and subject expertise vary by item. "
        "Language, nationality and a translated headline do not establish credibility.",
    ),
    **_entries(
        {"tass_en": "C", "cgtn_china": "C", "russia_mfa_ru": "C"},
        "Inherited editorial assignment with a state-controlled-source caution.",
        "Attributable outlet reporting, including statements of government positions.",
        "publisher",
        "State control is a source caution, not proof that every item is false. "
        "Attribution, claim content and conflicting evidence remain separate questions.",
    ),
    **_entries(
        {
            "yt_bbc_news": "B",
            "yt_reuters": "B",
            "yt_dw_news": "C",
            "yt_al_jazeera": "C",
            "yt_france24": "C",
            "yt_sky_news": "C",
        },
        "Inherited channel-specific editorial assignment for a configured named outlet "
        "channel, not a grade inherited from YouTube.",
        "The configured outlet channel's own publication metadata.",
        "publisher",
        "The connector does not authenticate video content or examine frames. "
        "YouTube hosting does not confer credibility on other channels or quoted sources.",
        "Legacy channel and RSS assignments can differ; this metadata does not silently "
        "reconcile them or claim a fresh performance assessment.",
    ),
    **_entries(
        {"gdelt_events": "C", "google_news_watchlists": "C", "gdelt_news": "C"},
        "Inherited collection-service assignment for machine-coded or aggregated reporting; "
        "the original publisher has not inherited a reliability grade from the platform.",
        "Discovery/index metadata and supplied excerpts, not the original publisher's reliability.",
        "aggregator",
        "Coverage, translation, extraction and syndication can distort results. A resolved "
        "publisher link does not establish source independence or upgrade the retained feed grade.",
    ),
    **_entries(
        {"isw_assessments": "B"},
        "Inherited editorial assignment for a named research institute's daily published "
        "assessment; the grade reflects consistent sourcing, not agreement with its conclusions.",
        "The institute's own daily assessment text, title and publication date.",
        "originator",
        "Assessments interpret partial open reporting and a declared analytical stance; "
        "an assessed line or claim is the institute's judgement, not an observed fact.",
    ),
    **_entries(
        {"ukraine_general_staff": "C"},
        "Inherited assignment for an official belligerent statement read through a public "
        "mirror that links each original post; a party to the conflict reporting its own count.",
        "Daily cumulative loss figures the General Staff publishes about its adversary.",
        "originator",
        "Figures are the claimant's own and are not independently verifiable; the mirror "
        "adds no assessment and a transcription error cannot be excluded.",
    ),
    **_entries(
        {"ucdp_candidate": "B"},
        "Inherited editorial assignment for a research programme's provisional monthly "
        "candidate event release, whether read from the public CSV or the token-gated API.",
        "Published candidate event records with their reported dates, places and counts.",
        "originator",
        "Candidate events are provisional and revised in later releases; coding, geocoding "
        "and fatality estimates are the programme's and can change.",
    ),
}
