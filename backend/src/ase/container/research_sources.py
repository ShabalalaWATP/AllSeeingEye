"""Static research capabilities, without asserting live availability or claim reliability."""

from ase.adapters.feeds.google_news import SPEC as GOOGLE_NEWS
from ase.adapters.feeds.rss_seeds_regional import REGIONAL_SEEDS
from ase.adapters.feeds.rss_seeds_social import SOCIAL_SEEDS
from ase.adapters.research.news import EDITIONS
from ase.adapters.research.news import LIMITATIONS as NEWS_LIMITATIONS
from ase.adapters.research.regional import LIMITATIONS as REGIONAL_LIMITATIONS
from ase.adapters.research_records.certificates import CertificateTransparencyProvider
from ase.adapters.research_records.companies_house import CompaniesHouseProvider
from ase.adapters.research_records.company import (
    SecCompanyDirectoryProvider,
    SecSubmissionsProvider,
)
from ase.adapters.research_records.domains import DNS_TYPES, RdapResearchProvider
from ase.adapters.research_records.ooni import LIMITATIONS as OONI_LIMITATIONS
from ase.adapters.research_records.ooni import OoniAggregateProvider
from ase.adapters.research_subjects.specs import subject_specs
from ase.container.research_spec import research_spec as _spec
from ase.domain.events import Category
from ase.domain.sources import SourceKind, SourceSpec


def _record_specs() -> tuple[SourceSpec, ...]:
    return (
        _spec(
            SecSubmissionsProvider.id,
            SecSubmissionsProvider.name,
            Category.ECONOMIC,
            "SEC EDGAR supplies filing metadata for an explicit CIK; issuing-record "
            "provenance does not verify a registrant's statements.",
            "Recent submission metadata in the requested filing-date interval.",
            "At most 20 records; no filing contents, older archive or ownership verification. "
            "CIK identity must be confirmed separately.",
            organisation="US Securities and Exchange Commission",
            role="originator",
        ),
        _spec(
            SecCompanyDirectoryProvider.id,
            SecCompanyDirectoryProvider.name,
            Category.ECONOMIC,
            "The SEC ticker directory supplies name and CIK identity candidates; "
            "a name match is not a confirmed identity.",
            "Current SEC ticker-directory candidates, not a complete company registry.",
            "At most eight candidates; no automatic identity merge or historical directory. "
            "Similarly named companies need not be the same entity.",
            organisation="US Securities and Exchange Commission",
            role="originator",
        ),
        _spec(
            CompaniesHouseProvider.id,
            CompaniesHouseProvider.name,
            Category.ECONOMIC,
            "Companies House supplies UK registry records and name-match candidates; "
            "registration and submitted particulars are not independently verified claims.",
            "Current company profile or first page of UK company-name candidates.",
            "Requires an operator-configured API key. At most 20 candidates; no filed "
            "documents, officer or ownership investigation, or historical snapshot.",
            "Prefer GB: or companies-house: prefixes; bare numbers can also match SEC CIKs. "
            "Registry jurisdiction does not establish company location.",
            organisation="Companies House",
            role="originator",
            requires_key=True,
        ),
        _spec(
            RdapResearchProvider.id,
            RdapResearchProvider.name,
            Category.CYBER,
            "Verisign supplies a registry RDAP response for an explicit domain; "
            "registry metadata does not identify its operator or owner.",
            "Current .com and .net registry snapshot only.",
            "No registrar referrals, other top-level domains or historical registration "
            "records. Redaction and omitted contacts limit attribution.",
            organisation="Verisign",
            role="originator",
        ),
        *(
            _spec(
                f"research-dns-{record_type.lower()}",
                f"Google Public DNS {record_type} records",
                Category.CYBER,
                f"Google Public DNS supplies a current {record_type} resolver answer; "
                "the resolver is the collector, not the domain's publisher or operator.",
                f"One explicit domain and {record_type} record type at collection time.",
                "No historical DNS or target-host connection. Shared addresses, mail servers "
                "and nameservers do not establish ownership or independence.",
                organisation="Google Public DNS",
                role="aggregator",
            )
            for record_type in DNS_TYPES
        ),
        _spec(
            CertificateTransparencyProvider.id,
            CertificateTransparencyProvider.name,
            Category.CYBER,
            "SSLMate aggregates certificate-transparency issuance records; logged names "
            "and issuer fields are verification leads, not proof of domain ownership.",
            "First page of unexpired certificate issuances matching one exact domain.",
            "Requires an operator-configured account API key. At most 20 records; no "
            "subdomain or wildcard expansion, complete history or latest-record guarantee.",
            "Certificate validity dates are not observation times. Certificates do not "
            "establish an active service, authenticity, trustworthiness or ownership.",
            organisation="SSLMate",
            role="aggregator",
            requires_key=True,
        ),
    )


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
    specs.extend(
        _spec(
            f"research_social_{seed.spec.id}",
            seed.spec.name,
            Category.SOCIAL,
            f"The configured {seed.spec.name} feed supplies account or publisher claims; "
            "neither the platform nor the configured label authenticates an item's origin.",
            "Local phrase matching within a configured RSS or Atom feed and requested dates.",
            "Only the first 200 feed items are considered; no platform-wide search, complete "
            "history, linked posts, replies or account authentication.",
            seed.spec.licence_note,
            role="platform",
            language=seed.spec.language,
            kind=SourceKind.RSS,
        )
        for seed in SOCIAL_SEEDS
        if seed.spec.id not in disabled
    )
    specs.extend(_record_specs())
    specs.extend(subject_specs())
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
    specs.extend(_private_specs())
    return tuple(spec for spec in specs if spec.id not in disabled)
