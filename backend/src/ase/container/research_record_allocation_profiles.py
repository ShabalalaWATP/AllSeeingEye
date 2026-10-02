"""Reviewed E01 allocation profiles for record and observation providers."""

from functools import partial

from ase.application.research.source_allocation_types import AllocationProfile
from ase.container.research_allocation_model import (
    COMPANY,
    DEFENCE,
    ECONOMY,
    NEWS,
    TECHNICAL,
    add_profile,
)


def record_allocation_profiles() -> dict[str, AllocationProfile]:
    result: dict[str, AllocationProfile] = {}
    # Primary means attributable records/measurements, not verified claims.
    record = partial(add_profile, result, prefix="")
    record(
        "research-uk-parliament",
        DEFENCE + "|parliament|policy|government|civilian|aid",
        "Parliament question and answer text; attributed assertions, not established findings.",
        countries=("GB",),
        primary=True,
    )
    record(
        "research-world-bank",
        ECONOMY + "|statistics|indicator|population|poverty|annual|data",
        "World Bank indicator values and units; current annual series, not historical vintages.",
        primary=True,
    )
    record(
        "research-ons-cpih",
        "ONS|CPIH|inflation|consumer|prices|index|monthly|statistics",
        "ONS monthly index values; explicit version, no latest-vintage or publication-date claim.",
        countries=("GB",),
        primary=True,
    )
    record(
        "research-cloudflare-radar-layer3 research-cloudflare-radar-layer7",
        "Cloudflare|Radar|DDoS|network|traffic|attack attacks|distribution|target|layer3|layer7",
        "Cloudflare distributions; provider denominators, no incident or attribution proof.",
        primary=True,
    )
    record(
        "research-sec-submissions research-sec-company-directory",
        COMPANY + "|SEC|filing|ticker|accounts",
        "SEC filing/directory metadata; underlying filings are not acquired as primary passages.",
    )
    record(
        "research-companies-house research-companies-house-officers research-companies-house-psc",
        COMPANY,
        "Registry fields and assertions; no verified beneficial ownership or historical snapshot.",
        countries=("GB",),
        primary=True,
    )
    record(
        "research-gleif-profile research-gleif-direct-parent research-gleif-ultimate-parent",
        COMPANY,
        "GLEIF assertions and accounting-consolidation links, not verified beneficial ownership.",
        primary=True,
    )
    record(
        "research-rdap",
        TECHNICAL,
        "Direct registry RDAP fields; registration does not establish operational ownership.",
        primary=True,
    )
    record(
        "research-dns-a research-dns-aaaa research-dns-mx research-dns-ns",
        TECHNICAL,
        "Current resolver observations; no historical infrastructure or identity/ownership proof.",
        primary=True,
    )
    record(
        "research-certificate-transparency",
        TECHNICAL + "|certificate|TLS",
        "Third-party certificate index; not direct service observation or ownership evidence.",
    )
    record(
        "research-contracts-finder",
        "procurement|contract|tender|award|supplier|spending|drone drones|defence",
        "Published notice assertions; no verified delivery or acquisition of linked originals.",
        countries=("GB",),
        primary=True,
    )
    record(
        "research-designations-uksl research-designations-ofac_sdn "
        "research-designations-un_sc research-designations-eu_fsf",
        COMPANY + "|sanctions|designation|asset|restriction",
        "Imported list records; provenance and identity remain unverified, no absence clearance.",
        primary=True,
    )
    record(
        "research-hapi-idps research-hapi-food-security research-hapi-operational-presence",
        "humanitarian|displacement|refugees|food security|aid|crisis|population",
        "HDX-distributed IOM/IPC/OCHA context; bounded sample, no independent conflict evidence.",
    )
    record(
        "research-asset-register",
        "cable cables|data centre datacentre|nuclear reactor|semiconductor chip fab|"
        "power station grid|refinery pipeline terminal|ground station teleport|"
        "infrastructure site facility|connectivity outage blackout",
        "Packaged map registers, gated by a reviewed asset phrase; not current site state.",
    )
    record(
        "research-aiddata-projects",
        "development|aid|China|loan|finance|infrastructure|project|energy|commitment",
        "Research project catalogue, not original loan agreements or disbursement evidence.",
    )
    record(
        "research-ooni-aggregate",
        "internet|connectivity|censorship|blocking|outage|network|OONI|measurement",
        "OONI measurements; anomalies do not establish interference, cause or attribution.",
        primary=True,
    )
    record(
        "research-openalex research-crossref",
        "academic|scholarly|paper|publication|journal|citation|research|study|science",
        "Overlapping scholarly metadata discovery, not paper acquisition.",
    )
    record(
        "research-usgs-area",
        "earthquake|seismic|hazard|magnitude|tremor|disaster",
        "USGS catalogue measurements; bounded geometry/time coverage and revision limits.",
        primary=True,
    )
    record(
        "research-osm-features",
        "church|mosque|station|bridge|stadium|airport|harbour|power plant|dam|hospital|"
        "tower|lighthouse|factory|mine|prison|military|river|lake|monument|castle|embassy|"
        "border|landmark|building",
        "OpenStreetMap features of the named kinds inside the drawn area; current map state.",
    )
    record(
        "research-eonet-area",
        "hazard|wildfire|storm|volcano|flood|disaster|weather",
        "NASA aggregation of hazard records; upstream origins and coverage need review.",
    )
    record(
        "research-openaq-area",
        "air|pollution|quality|particulate|environment|emissions",
        "Aggregated air-quality measurements; underlying stations and origins require review.",
    )
    record(
        "research-copernicus-footprints",
        "satellite|Sentinel|acquisition|footprint|imagery|observation",
        "Catalogue acquisition footprints only; no imagery or incident interpretation.",
        primary=True,
    )
    record(
        "research-retained-area-feeds",
        NEWS + "|hazard|satellite|vessel|flight|observation|area",
        "Mixed retained observations; source, geometry and dates need checks, no backfill.",
    )
    return result
