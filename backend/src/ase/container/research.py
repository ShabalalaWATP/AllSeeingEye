"""Concrete research provider selection and private store factories."""

from dataclasses import replace
from pathlib import Path
from typing import Literal

from ase.adapters.feeds.google_news import SPEC as GOOGLE_NEWS_SPEC
from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.research.eonet_area import EonetAreaResearchProvider
from ase.adapters.research.news import GoogleNewsResearchProvider
from ase.adapters.research.openaq_area import OpenAqAreaResearchProvider
from ase.adapters.research.retained_area import RetainedAreaFeedProvider
from ase.adapters.research.usgs_area import UsgsAreaResearchProvider
from ase.adapters.research_records.aiddata_provider import AidDataProvider
from ase.adapters.research_records.certificates import CertificateTransparencyProvider
from ase.adapters.research_records.companies_house import CompaniesHouseProvider
from ase.adapters.research_records.companies_house_client import CompaniesHouseClient
from ase.adapters.research_records.companies_house_people import (
    CompaniesHouseOfficersProvider,
    CompaniesHousePscProvider,
)
from ase.adapters.research_records.company import (
    SecCompanyDirectoryProvider,
    SecSubmissionsProvider,
)
from ase.adapters.research_records.contracts_finder import ContractsFinderProvider
from ase.adapters.research_records.copernicus import CopernicusFootprintProvider
from ase.adapters.research_records.copernicus_research import CopernicusResearchProvider
from ase.adapters.research_records.designation_import import load_designation_snapshot
from ase.adapters.research_records.designations import DesignationProvider
from ase.adapters.research_records.domains import DnsResearchProvider, RdapResearchProvider
from ase.adapters.research_records.gleif import GleifParentProvider, GleifProfileProvider
from ase.adapters.research_records.ooni import OoniAggregateProvider
from ase.adapters.research_records.sec_client import SecClient
from ase.adapters.research_subjects.parliament import ParliamentQuestionsProvider
from ase.adapters.research_subjects.scholarly import CrossrefProvider, OpenAlexProvider
from ase.adapters.research_subjects.world_bank import WorldBankProvider
from ase.adapters.store.memory import InMemoryEventStore
from ase.application.ports.feeds import EventStore
from ase.application.ports.geo import CountryDirectory
from ase.application.ports.research import ResearchProvider
from ase.application.ports.services import Clock
from ase.application.ports.source_controls import SourceAdmission
from ase.application.research.service import ResearchCollectionService
from ase.application.research.source_admission import ControlledResearchProvider
from ase.container.research_feeds import public_research_feeds
from ase.domain.research import ResearchFocus, ResearchQuery
from ase.domain.source_controls import source_control_keys


def research_service(
    http: FeedHttpClient,
    clock: Clock,
    disabled: tuple[str, ...] = (),
    *,
    admission: SourceAdmission | None = None,
    retained_store: EventStore | None = None,
    sec_client: SecClient | None = None,
    ooni_noncommercial_use_acknowledged: bool = False,
    uksl_snapshot_path: str | None = None,
    ofac_sdn_snapshot_path: str | None = None,
    aiddata_catalogue_path: str | None = None,
    countries: CountryDirectory | None = None,
    companies_house_key: str | None = None,
    certificate_transparency_key: str | None = None,
    openalex_api_key: str | None = None,
    openaq_api_key: str | None = None,
) -> ResearchCollectionService:
    sec_client = sec_client or SecClient(http)
    # Preserve the credential-specific rolling request allowance across research runs.
    registry_client = CompaniesHouseClient(http, clock, companies_house_key)
    openaq = OpenAqAreaResearchProvider(http, clock, openaq_api_key)
    companies_house = CompaniesHouseProvider(
        http, clock, companies_house_key, client=registry_client
    )
    certificates = CertificateTransparencyProvider(http, clock, certificate_transparency_key)
    procurement = ContractsFinderProvider(http, clock)
    aiddata = AidDataProvider(
        Path(aiddata_catalogue_path) if aiddata_catalogue_path else None,
        clock,
        {country.iso3: country.iso2 for country in countries.countries()} if countries else {},
    )
    snapshots: tuple[tuple[Literal["uksl", "ofac_sdn"], str | None], ...] = (
        ("uksl", uksl_snapshot_path),
        ("ofac_sdn", ofac_sdn_snapshot_path),
    )
    designations = tuple(
        DesignationProvider(
            load_designation_snapshot(Path(path)) if path else None, clock, authority
        )
        for authority, path in snapshots
    )

    def providers(query: ResearchQuery) -> list[ResearchProvider]:
        if query.focus in (ResearchFocus.DOCUMENT, ResearchFocus.MEDIA):
            # Analysing a private upload does not send its extracted terms to public feeds.
            return []
        selected: list[ResearchProvider] = []
        if query.area is not None:
            # Fresh dated geometry wins duplicate identities from retained feeds.
            selected.extend(
                (
                    UsgsAreaResearchProvider(http, clock),
                    EonetAreaResearchProvider(http, clock),
                    openaq,
                )
            )
        if query.area is not None and retained_store is not None:
            selected.append(
                RetainedAreaFeedProvider(retained_store, admission=admission, disabled=disabled)
            )
        if query.focus == ResearchFocus.COMPANY:
            selected.extend(
                (
                    SecSubmissionsProvider(http, clock, client=sec_client),
                    SecCompanyDirectoryProvider(http, clock, client=sec_client),
                    companies_house,
                    CompaniesHouseOfficersProvider(registry_client, clock),
                    CompaniesHousePscProvider(registry_client, clock),
                    GleifProfileProvider(http, clock),
                    GleifParentProvider(http, clock, "direct"),
                    GleifParentProvider(http, clock, "ultimate"),
                )
            )
        elif query.focus == ResearchFocus.DOMAIN:
            selected.extend((RdapResearchProvider(http, clock), certificates))
            dns_types = ("A", "AAAA", "MX", "NS") if query.mode.requires_challenge else ("A",)
            selected.extend(DnsResearchProvider(http, clock, kind) for kind in dns_types)
        if GOOGLE_NEWS_SPEC.id not in disabled:
            selected.extend(
                GoogleNewsResearchProvider(http, clock, language)
                for language in dict.fromkeys(query.languages)
            )
        selected.extend(
            (
                procurement,
                aiddata,
                CopernicusResearchProvider(CopernicusFootprintProvider(http, clock)),
                *designations,
                OpenAlexProvider(http, clock, api_key=openalex_api_key),
                CrossrefProvider(http, clock),
                WorldBankProvider(http, clock),
                ParliamentQuestionsProvider(http, clock),
                OoniAggregateProvider(
                    http, clock, allow_noncommercial_data=ooni_noncommercial_use_acknowledged
                ),
            )
        )
        selected.extend(public_research_feeds(http, clock, spatial=query.area is not None))
        # Keep unsupported and unselected capabilities visible in the bounded
        # catalogue. Admission and execution budgets are enforced independently.
        return [
            ControlledResearchProvider(provider, admission)
            if admission is not None and not isinstance(provider, RetainedAreaFeedProvider)
            else provider
            for provider in selected
            if not any(key in disabled for key in source_control_keys(provider.id))
        ]

    def challenge_providers(query: ResearchQuery) -> list[ResearchProvider]:
        if query.focus in (ResearchFocus.DOCUMENT, ResearchFocus.MEDIA):
            return []
        # Registry/DNS snapshots ignore contrary search terms. Re-fetching them
        # for every judgement would exhaust the challenge budget without searching.
        return [
            provider
            for provider in providers(replace(query, focus=ResearchFocus.GENERAL))
            if provider.id
            not in {
                RetainedAreaFeedProvider.id,
                UsgsAreaResearchProvider.id,
                EonetAreaResearchProvider.id,
                OpenAqAreaResearchProvider.id,
            }
        ]

    return ResearchCollectionService(providers, challenge_providers=challenge_providers)


def private_research_store() -> InMemoryEventStore:
    return InMemoryEventStore(memory_budget_bytes=8 * 1024 * 1024)
