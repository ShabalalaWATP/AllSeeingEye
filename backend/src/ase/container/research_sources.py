"""Static research capabilities, without asserting live availability or claim reliability."""

from datetime import timedelta

from ase.adapters.feeds.google_news import SPEC as GOOGLE_NEWS
from ase.adapters.feeds.rss_seeds_social import SOCIAL_SEEDS
from ase.adapters.research.news import EDITIONS
from ase.adapters.research.news import LIMITATIONS as NEWS_LIMITATIONS
from ase.adapters.research_records.certificates import CertificateTransparencyProvider
from ase.adapters.research_records.companies_house import CompaniesHouseProvider
from ase.adapters.research_records.company import (
    SecCompanyDirectoryProvider,
    SecSubmissionsProvider,
)
from ase.adapters.research_records.domains import DNS_TYPES, RdapResearchProvider
from ase.domain.events import Category, Reliability
from ase.domain.source_rating_catalog import ProvenanceRole
from ase.domain.source_ratings import SOURCE_RATING_POLICY_VERSION, SourceRating
from ase.domain.sources import SourceKind, SourceSpec

COMMON_LIMITATIONS = (
    "Reliability remains unassessed (F); collection does not verify individual claims, "
    "publishers, accounts or uploaders. No measured accuracy or review date is recorded.",
    "This catalogue describes supported capabilities, not current availability, credentials "
    "or successful collection. Report collection receipts record actual coverage.",
)


def _spec(
    id_: str,
    name: str,
    category: Category,
    basis: str,
    scope: str,
    *limitations: str,
    organisation: str = "",
    role: ProvenanceRole = "unassessed",
    language: str = "en",
    kind: SourceKind = SourceKind.API,
    requires_key: bool = False,
) -> SourceSpec:
    # Empty organisations share unknown provenance and establish no independent origin.
    # Named collector organisations group endpoints, not the underlying claims.
    return SourceSpec(
        id=id_,
        name=name,
        organisation=organisation,
        category=category,
        kind=kind,
        url="",
        reliability=Reliability.F,
        poll_interval=timedelta(days=1),
        language=language,
        requires_key=requires_key,
        flags=frozenset({"on_demand", "unassessed"}),
        rating=SourceRating(
            policy_version=SOURCE_RATING_POLICY_VERSION,
            status="unassessed",
            assessed_grade=None,
            basis=basis,
            scope=scope,
            limitations=(*COMMON_LIMITATIONS, *limitations),
            provenance_role=role,
            publisher_reliability_assessed=False,
        ),
    )


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
    specs.extend(_private_specs())
    return tuple(spec for spec in specs if spec.id not in disabled)
