"""Unassessed corporate and domain research capability descriptions."""

from ase.adapters.research_records.certificates import CertificateTransparencyProvider
from ase.adapters.research_records.companies_house import CompaniesHouseProvider
from ase.adapters.research_records.company import (
    SecCompanyDirectoryProvider,
    SecSubmissionsProvider,
)
from ase.adapters.research_records.domains import DNS_TYPES, RdapResearchProvider
from ase.container.research_spec import research_spec as _spec
from ase.domain.events import Category
from ase.domain.sources import SourceSpec


def record_specs() -> tuple[SourceSpec, ...]:
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
