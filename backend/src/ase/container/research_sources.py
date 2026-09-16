"""Static research capabilities, without asserting live availability or claim reliability."""

from dataclasses import replace

from ase.adapters.feeds.google_news import SPEC as GOOGLE_NEWS
from ase.adapters.feeds.radar_attack_trends import SPEC as RADAR_ATTACK_SPEC
from ase.adapters.feeds.rss_seeds_regional import REGIONAL_SEEDS
from ase.adapters.research.news import EDITIONS
from ase.adapters.research.news import LIMITATIONS as NEWS_LIMITATIONS
from ase.adapters.research.regional import LIMITATIONS as REGIONAL_LIMITATIONS
from ase.adapters.research.retained_area import RetainedAreaFeedProvider
from ase.adapters.research.youtube import SOURCE_ID as YOUTUBE_RESEARCH_ID
from ase.adapters.research_records.cloudflare_radar import PROVIDER_IDS as RADAR_PROVIDER_IDS
from ase.adapters.research_records.ecb_reference_rate import EcbReferenceRateProvider
from ase.adapters.research_records.ioda_outage_events import IodaOutageResearchProvider
from ase.adapters.research_records.ooni import LIMITATIONS as OONI_LIMITATIONS
from ase.adapters.research_records.ooni import OoniAggregateProvider
from ase.adapters.research_subjects.specs import subject_specs
from ase.container.research_feed_specs import additional_feed_specs
from ase.container.research_record_specs import record_specs
from ase.container.research_spec import research_spec as _spec
from ase.container.research_web_spec import web_search_spec
from ase.domain.events import Category
from ase.domain.source_controls import source_control_keys
from ase.domain.sources import SourceKind, SourceSpec


def _private_specs() -> tuple[SourceSpec, ...]:
    return (
        _spec(
            "research_import",
            "Private document import",
            Category.NEWS,
            "An authenticated user supplied a document; extracted text and local references "
            "do not authenticate the author or document.",
            "Bounded passages from private TXT, CSV, JSON, PDF and DOCX uploads.",
            "Extraction can omit unsupported content, scanned pages and material beyond "
            "size, page or text limits. Upload capture time is not publication time.",
            "Uploader identity is not independent provenance. Private input access remains "
            "controlled separately from this capability description.",
            language="und",
        ),
        _spec(
            "research_media",
            "Private image and video import",
            Category.NEWS,
            "An authenticated user supplied media; metadata, OCR and sampled frame references "
            "are unverified leads, not an authenticity assessment.",
            "Bounded image metadata and English OCR, plus up to three video keyframes.",
            "Requires available local extraction runtimes. Supported images and videos "
            "are subject to byte, pixel, duration and execution limits.",
            "OCR and sparse sampling can miss or misread content. Metadata can be altered; "
            "frame offsets and upload time do not establish recording date or place.",
            language="und",
        ),
    )


def research_source_specs(disabled: tuple[str, ...] = ()) -> tuple[SourceSpec, ...]:
    """Describe exact event source IDs; disabled parent feeds suppress their derivatives."""
    specs: list[SourceSpec] = []
    if GOOGLE_NEWS.id not in disabled:
        specs.extend(
            _spec(
                f"research_google_news_{language}",
                f"Google News research ({language})",
                Category.NEWS,
                "Google News collects search-feed links from underlying publishers; Google's "
                "platform identity does not assess those publishers or their claims.",
                f"Question-specific RSS search using the {language} edition and supplied phrases.",
                NEWS_LIMITATIONS,
                role="aggregator",
                language=language,
                kind=SourceKind.RSS,
            )
            for language in EDITIONS
        )
    specs.append(
        _spec(
            YOUTUBE_RESEARCH_ID,
            "YouTube video search",
            Category.SOCIAL,
            "One platform-wide YouTube search returns uploader-supplied metadata; neither "
            "YouTube nor a channel label authenticates an uploader or an item's origin.",
            "Bounded search-result titles, channel labels, upload dates and links within "
            "the requested publication interval.",
            "Requires a configured YouTube Data API key; the channel Atom feeds are "
            "disallowed by youtube.com/robots.txt, so there is no public alternative.",
            "At most 20 results from one request, subject to a local daily search "
            "allowance. No complete archive, transcripts, captions, comments or media.",
            "YouTube Data API v3 terms; titles, links and a bounded excerpt only",
            role="platform",
            language="und",
            requires_key=True,
        )
    )
    specs.extend(record_specs())
    specs.extend(subject_specs())
    specs.extend(
        replace(
            _spec(
                provider_id,
                f"Cloudflare Radar {layer} target distribution",
                Category.CYBER,
                "Provider-reported traffic shares; no incidents, target locations or attribution.",
                "Current global top-10 distribution; one fixed-layer request per cache miss.",
                "Explicit noncommercial acknowledgement and configured Radar token required. "
                "No history, precise geometry, full country coverage or query-text filtering. "
                "Country filtering preserves the global denominator and full provider interval.",
                RADAR_ATTACK_SPEC.licence_note,
                organisation="Cloudflare Radar",
                role="originator",
                requires_key=True,
            ),
            licence_note=RADAR_ATTACK_SPEC.licence_note,
        )
        for layer, provider_id in RADAR_PROVIDER_IDS.items()
    )
    specs.append(
        _spec(
            RetainedAreaFeedProvider.id,
            RetainedAreaFeedProvider.name,
            Category.NEWS,
            "Area collection preserves original feed identities and grades; no new source trust.",
            RetainedAreaFeedProvider.spatial_scope,
            RetainedAreaFeedProvider.temporal_scope,
            role="aggregator",
        )
    )
    specs.append(
        _spec(
            "research-aiddata-projects",
            "AidData Chinese development projects",
            Category.ECONOMIC,
            "Imported historical project assertions; source authenticity and "
            "outcomes are unverified.",
            "Local country/term search by commitment year, at most 20 records with "
            "declared limits.",
            "Requires a local catalogue and explicit recorded-time selection. No "
            "automatic download "
            "or complete-release claim; commitments are not payments. Exact area intersection "
            "uses only supplied project geometry and explicit recorded commitment years.",
            "AidData ODC-By; OSM geometry ODbL. Attribute both; preserve "
            "source-specific reuse terms.",
            organisation="AidData",
            role="originator",
        )
    )
    specs.append(
        _spec(
            "research-copernicus-footprints",
            "Copernicus satellite footprints",
            Category.SPACE,
            "Catalogue acquisition metadata, not an interpretation or authentication of imagery.",
            "Explicit bounded area and dates, up to 20 Sentinel-2 L2A catalogue footprints.",
            "No imagery or assets fetched; dates and cloud coverage are provider metadata. "
            "Area and dates are disclosed to the catalogue only after operator selection.",
            organisation="Copernicus Data Space Ecosystem",
            role="originator",
        )
    )
    specs.append(
        _spec(
            "research-contracts-finder",
            "Contracts Finder publication notices",
            Category.ECONOMIC,
            "Official publication records contain submitted claims, not verified fulfilment.",
            "One publication-date page of at most 20 OCDS releases, locally phrase-matched.",
            "No complete procurement history, company identity resolution or additional pages. "
            "Publication is not proof of award performance or misconduct.",
            organisation="UK Contracts Finder",
            role="originator",
        )
    )
    specs.extend(
        _spec(
            f"research-designations-{authority}",
            name,
            Category.ECONOMIC,
            "Operator-imported designation snapshot; source authenticity not verified.",
            "Exact authority ID or full-name candidate matching, up to 20 results.",
            "Requires a validated local snapshot. Date, source hash and reuse terms retained. "
            "A name match is not verified identity or guilt; absence is not clearance.",
            organisation=organisation,
            role="originator",
        )
        for authority, name, organisation in (
            ("uksl", "UK Sanctions List imported snapshot", "UK FCDO"),
            ("ofac_sdn", "OFAC SDN imported snapshot", "US Treasury OFAC"),
        )
    )
    specs.append(
        _spec(
            OoniAggregateProvider.id,
            OoniAggregateProvider.name,
            Category.CYBER,
            "OONI country aggregates are observations, not verified causes or attribution.",
            "Country/day web-connectivity counters over an explicit interval of at most 14 days.",
            OONI_LIMITATIONS,
            "Requires operator acknowledgement of appropriate CC BY-NC-SA 4.0 use. "
            "Disabled by default; no individual probe records are collected.",
            organisation="Open Observatory of Network Interference",
            role="originator",
        )
    )
    specs.extend(
        (
            _spec(
                IodaOutageResearchProvider.id,
                IodaOutageResearchProvider.name,
                Category.CYBER,
                "IODA reports detected country-level network anomaly windows; it does not "
                "establish outage cause, affected users, a precise location or cyber attribution.",
                "Exact one-country recorded-time selection; at most 14 days and the first "
                "20 returned events from one request.",
                "Requires operator-reviewed data-use acknowledgement. IODA API results carry "
                "copyright; no complete-history or absence claim, and long-term reuse "
                "needs review.",
                "Source: IODA, Georgia Tech. API copyright notice; data-reuse permission "
                "must be confirmed by the operator.",
                organisation="Georgia Tech Internet Intelligence Lab",
                role="originator",
            ),
            _spec(
                EcbReferenceRateProvider.id,
                EcbReferenceRateProvider.name,
                Category.ECONOMIC,
                "Official ECB EXR reference-rate values, not a market transaction quote or "
                "a verified economic interpretation.",
                "Exact GBP-per-EUR series and at most 31 recorded days; no broad economic search.",
                "Current API vintage only. Missing days are not zero; revisions, release "
                "timestamps and other ECB series are not acquired.",
                "Source: ECB statistics. Public ESCB data reuse requires attribution and "
                "unmodified values and metadata.",
                organisation="European Central Bank",
                role="originator",
            ),
        )
    )
    specs.extend(
        _spec(
            f"research-companies-house-{kind}",
            f"Companies House {label}",
            Category.ECONOMIC,
            "Registry-reported assertions; identity and control are not independently verified.",
            "Current first-page registry context for an explicit UK company identifier.",
            "At most 20 records per request. Names remain candidates; no cross-source person "
            "merging, complete historical register or absence-of-control inference.",
            organisation="Companies House",
            role="originator",
            requires_key=True,
        )
        for kind, label in (("officers", "officers"), ("psc", "persons with significant control"))
    )
    specs.extend(
        _spec(
            f"research-gleif-{kind}",
            f"GLEIF {label}",
            Category.ECONOMIC,
            "GLEIF registry assertions remain unassessed; registration does not verify claims.",
            "Current exact-LEI profile or reported accounting consolidation parent.",
            "One record per request. Accounting parents are not a complete beneficial ownership "
            "graph. Missing relationships do not establish absence of a parent.",
            organisation="GLEIF",
            role="originator",
        )
        for kind, label in (
            ("profile", "legal entity profile"),
            ("direct-parent", "direct parent"),
            ("ultimate-parent", "ultimate parent"),
        )
    )
    specs.extend(
        _spec(
            f"research_regional_{seed.spec.id}",
            seed.spec.name,
            seed.spec.category,
            "Publisher-supplied regional headlines; source and claim remain unassessed.",
            "Local phrase matching in a bounded recent public RSS snapshot.",
            REGIONAL_LIMITATIONS,
            seed.spec.licence_note,
            organisation=seed.spec.organisation,
            language=seed.spec.language,
            kind=SourceKind.RSS,
            role="aggregator" if seed.spec.id == "cdt_zh" else "unassessed",
        )
        for seed in REGIONAL_SEEDS
        if seed.spec.id not in disabled
    )
    specs.extend(additional_feed_specs())
    specs.extend(_private_specs())
    specs.append(web_search_spec())
    return tuple(
        spec for spec in specs if not any(key in disabled for key in source_control_keys(spec.id))
    )
