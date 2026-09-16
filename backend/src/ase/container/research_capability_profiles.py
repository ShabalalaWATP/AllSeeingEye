"""Reviewed non-feed research support. Entries describe implemented routes, not live access."""

from dataclasses import dataclass, replace

from ase.domain.source_capabilities import (
    CapabilityPrerequisite,
    CapabilitySupport,
)
from ase.domain.source_capabilities import (
    CapabilityScope as Scope,
)
from ase.domain.source_capabilities import (
    ContentCapability as Content,
)
from ase.domain.source_capabilities import (
    DateSupport as Dates,
)
from ase.domain.source_capabilities import (
    ExecutionRoute as Route,
)
from ase.domain.source_capabilities import (
    LanguageSupport as Language,
)
from ase.domain.source_capabilities import (
    PrerequisiteKind as Need,
)


@dataclass(frozen=True, slots=True)
class CapabilityProfile:
    family: str
    support: CapabilitySupport
    content: Content = Content.STRUCTURED
    route: Route = Route.PUBLIC_RESEARCH
    prerequisites: tuple[CapabilityPrerequisite, ...] = ()
    unknown_origin: bool = False


def _profile(
    family: str,
    scopes: tuple[Scope, ...],
    date: Dates | tuple[Dates, ...],
    constraints: str,
    *,
    prerequisite: CapabilityPrerequisite | None = None,
    english_terms: bool = False,
    unknown_origin: bool = False,
    content: Content = Content.STRUCTURED,
    route: Route = Route.PUBLIC_RESEARCH,
) -> CapabilityProfile:
    return CapabilityProfile(
        family,
        CapabilitySupport(
            scopes,
            date if isinstance(date, tuple) else (date,),
            ("en",) if english_terms else (),
            Language.ENGLISH_TERMS if english_terms else Language.NOT_FILTERED,
            constraints,
        ),
        content,
        route,
        (prerequisite,) if prerequisite else (),
        unknown_origin,
    )


def structured_profiles() -> dict[str, CapabilityProfile]:
    """Explicit IDs intentionally fail inventory construction when new routes lack review."""
    profiles = {
        "research-sec-submissions": _profile(
            "corporate",
            (Scope.COMPANY,),
            Dates.PUBLICATION_INTERVAL,
            "Company focus and explicit SEC CIK; filing metadata only, bounded history pages.",
        ),
        "research-sec-company-directory": _profile(
            "corporate",
            (Scope.COMPANY,),
            Dates.CURRENT_SNAPSHOT,
            "Company focus and name or ticker without a resolved CIK; identity candidates only.",
        ),
        "research-youtube": _profile(
            "social",
            (Scope.TOPIC, Scope.COUNTRY_CONTEXT),
            Dates.PUBLICATION_INTERVAL,
            "Bounded explicit phrases and a publication interval; one platform-wide search "
            "request, at most 20 results, under a local daily search allowance. Uploader "
            "metadata only: no channel curation, transcripts, captions, comments or media, "
            "and no geographic or language verification.",
            prerequisite=CapabilityPrerequisite(Need.API_KEY, "ASE_YOUTUBE_API_KEY"),
            unknown_origin=True,
            content=Content.DISCOVERY,
        ),
        "research-rdap": _profile(
            "technical",
            (Scope.DOMAIN,),
            Dates.CURRENT_SNAPSHOT,
            "Domain focus and explicit second-level .com/.net domain; no referrals or owner proof.",
        ),
        "research-certificate-transparency": _profile(
            "technical",
            (Scope.DOMAIN,),
            Dates.CURRENT_SNAPSHOT,
            "Domain focus and exact domain; bounded unexpired issuances, no subdomain expansion.",
            prerequisite=CapabilityPrerequisite(Need.API_KEY, "ASE_CERTIFICATE_TRANSPARENCY_KEY"),
            unknown_origin=True,
        ),
        "research-world-bank": _profile(
            "macro",
            (Scope.COUNTRY_CONTEXT,),
            Dates.ANNUAL_PERIODS,
            "General focus, explicit country/indicator/year subject and compatible country; "
            "at most 20 annual periods. "
            "Current values and units, no historical vintages.",
        ),
        "research-ons-cpih": _profile(
            "macro",
            (Scope.TOPIC, Scope.COUNTRY_CONTEXT),
            Dates.RECORDED_INTERVAL,
            "Exact ONS:CPIH:<version> subject; UK all-items CPIH only, at most 24 monthly "
            "observations from one selected version. Months are not publication dates; "
            "no automatic latest-version discovery or other series. No area filtering.",
        ),
        "research-ecb-gbp-reference-rate": _profile(
            "macro",
            (Scope.TOPIC, Scope.COUNTRY_CONTEXT),
            Dates.RECORDED_INTERVAL,
            "Exact ECB:EXR:GBP subject, recorded time and at most 31 days. Current "
            "GBP-per-EUR daily reference rates, no other series or historical vintages. "
            "GB is only a currency-related brief context, not incident geography.",
        ),
        "research-ioda-outage-events": _profile(
            "network",
            (Scope.COUNTRY_CONTEXT,),
            Dates.RECORDED_INTERVAL,
            "One exact country, IODA:CC or explicit source selection, recorded interval at "
            "most 14 days; first 20 events only. Country is not a precise outage site.",
            prerequisite=CapabilityPrerequisite(
                Need.ACKNOWLEDGEMENT, "ASE_IODA_PUBLIC_DATA_USE_ACKNOWLEDGED"
            ),
        ),
        "research-uk-parliament": _profile(
            "official",
            (Scope.TOPIC, Scope.COUNTRY_CONTEXT),
            Dates.PUBLICATION_INTERVAL,
            "General focus, explicit source or parliament: subject and English terms; "
            "GB country only.",
            english_terms=True,
        ),
        "research_social_bluesky": _profile(
            "social",
            (Scope.TOPIC, Scope.COUNTRY_CONTEXT),
            Dates.PUBLICATION_INTERVAL,
            "Explicit bounded phrases select at most three reviewed public accounts; one "
            "admitted task reads those author feeds and matches phrases locally. No "
            "platform-wide search, archive, repost, foreign reply, linked page or media. "
            "A curated topic is a collection choice, not incident geography.",
            unknown_origin=True,
            content=Content.DISCOVERY,
        ),
        "research-retained-area-feeds": _profile(
            "area",
            (Scope.AREA,),
            Dates.RESEARCH_INTERVAL,
            "General focus and area polygon; retained precise geometry, source admission and "
            "item time checks apply. No backfill, refresh or country-centroid substitution.",
            prerequisite=CapabilityPrerequisite(Need.RETAINED_STORE, None),
            unknown_origin=True,
            content=Content.RETAINED,
            route=Route.RETAINED_AREA,
        ),
        "research-aiddata-projects": _profile(
            "development",
            (Scope.TOPIC, Scope.COUNTRY_CONTEXT, Scope.AREA),
            Dates.RECORDED_INTERVAL,
            "General focus, explicit source and recorded commitment-year interval; bounded local "
            "project lookup, at most one country. Supplied geometry only for area intersection.",
            prerequisite=CapabilityPrerequisite(Need.CATALOGUE, "ASE_AIDDATA_CATALOGUE_PATH"),
        ),
        "research-copernicus-footprints": _profile(
            "space",
            (Scope.AREA,),
            # Acquisition time is an observation time: area research and explicit
            # recorded-time requests can both use it.
            (Dates.RESEARCH_INTERVAL, Dates.RECORDED_INTERVAL),
            "General focus and valid bounded rectangular area/date query; Sentinel-2 L2A "
            "acquisition footprints only. No imagery or incident interpretation.",
        ),
        "research-contracts-finder": _profile(
            "procurement",
            (Scope.TOPIC, Scope.COUNTRY_CONTEXT, Scope.COMPANY),
            Dates.PUBLICATION_INTERVAL,
            "General/company focus and explicit terms; no country conflict with GB; one page.",
        ),
        "research-ooni-aggregate": _profile(
            "network",
            (Scope.COUNTRY_CONTEXT,),
            Dates.RECORDED_INTERVAL,
            "One explicit country or ooni:CC subject and at most 14 days; daily web-connectivity "
            "counters are observations, not evidence of cause or attribution.",
            prerequisite=CapabilityPrerequisite(
                Need.ACKNOWLEDGEMENT, "ASE_OONI_NONCOMMERCIAL_USE_ACKNOWLEDGED"
            ),
        ),
        "research_import": _profile(
            "private_input",
            (Scope.PRIVATE_INPUT,),
            Dates.INPUT_METADATA,
            "Authenticated scoped upload; document extraction limits apply. Capture time is "
            "not publication time; this route is not a public research provider.",
            prerequisite=CapabilityPrerequisite(Need.PRIVATE_INPUT, None),
            unknown_origin=True,
            content=Content.PRIVATE_PASSAGES,
            route=Route.PRIVATE_DOCUMENT,
        ),
        "research_media": _profile(
            "private_input",
            (Scope.PRIVATE_INPUT,),
            Dates.INPUT_METADATA,
            "Authenticated scoped media upload and local tools; English OCR and bounded frames. "
            "Metadata does not establish recording place, time or authenticity.",
            prerequisite=CapabilityPrerequisite(Need.RUNTIME, "ASE_RESEARCH_TESSERACT_PATH"),
            unknown_origin=True,
            content=Content.PRIVATE_MEDIA,
            route=Route.PRIVATE_MEDIA,
        ),
        "research-web-search": _profile(
            "web_discovery",
            (Scope.TOPIC, Scope.COUNTRY_CONTEXT),
            Dates.PUBLICATION_INTERVAL,
            "Separate opt-in destination model web discovery allocation, not a ResearchProvider. "
            "Generated discovery results do not establish original-passage acquisition.",
            prerequisite=CapabilityPrerequisite(Need.MODEL, None),
            unknown_origin=True,
            content=Content.DISCOVERY,
            route=Route.FRESH_WEB,
        ),
    }
    for layer in ("layer3", "layer7"):
        radar = _profile(
            "network",
            (Scope.TOPIC, Scope.COUNTRY_CONTEXT),
            Dates.RESEARCH_INTERVAL,
            "Explicit source or radar:global/radar:CC, English, global or one country; current "
            "one-day global top-10 target distribution only. Whole provider intervals, "
            "shares and denominator units; no historical query, incident count or attribution. "
            "Requires a configured token AND explicit CC BY-NC 4.0 acknowledgement.",
            prerequisite=CapabilityPrerequisite(
                Need.ACKNOWLEDGEMENT, "ASE_CLOUDFLARE_RADAR_NONCOMMERCIAL_USE_ACKNOWLEDGED"
            ),
            english_terms=True,
        )
        profiles[f"research-cloudflare-radar-{layer}"] = replace(
            radar,
            support=replace(
                radar.support, dates=(Dates.RESEARCH_INTERVAL, Dates.RECORDED_INTERVAL)
            ),
        )
    for suffix in ("", "-officers", "-psc"):
        profiles[f"research-companies-house{suffix}"] = _profile(
            "corporate",
            (Scope.COMPANY,),
            Dates.CURRENT_SNAPSHOT,
            "Company focus and compatible GB country. Profile permits name candidates; officers "
            "and PSC require explicit company number. One page, no verified identity or control.",
            prerequisite=CapabilityPrerequisite(Need.API_KEY, "ASE_COMPANIES_HOUSE_KEY"),
        )
    for suffix in ("profile", "direct-parent", "ultimate-parent"):
        profiles[f"research-gleif-{suffix}"] = _profile(
            "corporate",
            (Scope.COMPANY,),
            Dates.CURRENT_SNAPSHOT,
            "Company focus and exact LEI; one current record, no complete ownership graph.",
        )
    for suffix in ("a", "aaaa", "mx", "ns"):
        profiles[f"research-dns-{suffix}"] = _profile(
            "technical",
            (Scope.DOMAIN,),
            Dates.CURRENT_SNAPSHOT,
            "Domain focus and exact domain; A in all depths, other types in Deep/Advanced. "
            "Resolver observation does not establish domain ownership.",
            unknown_origin=True,
        )
    for authority, setting in (
        ("uksl", "ASE_UKSL_SNAPSHOT_PATH"),
        ("ofac_sdn", "ASE_OFAC_SDN_SNAPSHOT_PATH"),
    ):
        profiles[f"research-designations-{authority}"] = _profile(
            "sanctions",
            (Scope.TOPIC, Scope.COMPANY),
            Dates.CURRENT_SNAPSHOT,
            "General/company focus, explicit source or authority-prefixed identifier/full name. "
            "Imported snapshot candidates are not verified identity or absence clearance.",
            prerequisite=CapabilityPrerequisite(Need.SNAPSHOT, setting),
        )
    for name in ("openalex", "crossref"):
        profiles[f"research-{name}"] = _profile(
            "scholarly",
            (Scope.TOPIC,),
            Dates.PUBLICATION_INTERVAL,
            "General focus, explicit source or academic: subject, English terms and no country "
            "filter. Publication metadata only; overlapping aggregators, no full text.",
            english_terms=True,
            unknown_origin=True,
            content=Content.DISCOVERY,
            prerequisite=(
                CapabilityPrerequisite(Need.API_KEY, "ASE_OPENALEX_API_KEY", True)
                if name == "openalex"
                else None
            ),
        )
    profiles["research_social_telegram"] = _profile(
        "social",
        (Scope.TOPIC, Scope.COUNTRY_CONTEXT),
        Dates.PUBLICATION_INTERVAL,
        "Explicit bounded phrases and a post-time interval, matched locally inside one "
        "curated public Telegram channel preview chosen by declared language and subject "
        "fit. Not a Telegram search, an archive, or a sweep of the curated set. Every "
        "curated channel is a party to, or aligned with, what it reports, so a match is a "
        "participant's claim and establishes neither geography nor corroboration.",
        unknown_origin=True,
        content=Content.DISCOVERY,
    )
    for name in ("usgs", "eonet", "openaq"):
        profiles[f"research-{name}-area"] = _profile(
            "environment" if name == "openaq" else "hazard",
            (Scope.AREA,),
            Dates.RESEARCH_INTERVAL,
            "General focus and bounded area; acquisition/observation interval, no country "
            "filter. Provider-specific interval, geometry, dataset and reuse checks apply.",
            unknown_origin=name != "usgs",
            prerequisite=(
                CapabilityPrerequisite(Need.API_KEY, "ASE_OPENAQ_API_KEY")
                if name == "openaq"
                else None
            ),
        )
    return profiles
