"""Concrete research provider selection and private store factories."""

from dataclasses import replace

from ase.adapters.feeds.google_news import SPEC as GOOGLE_NEWS_SPEC
from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.feeds.rss_seeds_social import SOCIAL_SEEDS
from ase.adapters.research.news import GoogleNewsResearchProvider
from ase.adapters.research.social import SocialFeedResearchProvider
from ase.adapters.research_records.certificates import CertificateTransparencyProvider
from ase.adapters.research_records.companies_house import CompaniesHouseProvider
from ase.adapters.research_records.company import (
    SecCompanyDirectoryProvider,
    SecSubmissionsProvider,
)
from ase.adapters.research_records.domains import DnsResearchProvider, RdapResearchProvider
from ase.adapters.store.memory import InMemoryEventStore
from ase.application.ports.research import ResearchProvider
from ase.application.ports.services import Clock
from ase.application.research.service import ResearchCollectionService
from ase.domain.research import ResearchFocus, ResearchMode, ResearchQuery


def research_service(
    http: FeedHttpClient,
    clock: Clock,
    disabled: tuple[str, ...] = (),
    *,
    companies_house_key: str | None = None,
    certificate_transparency_key: str | None = None,
) -> ResearchCollectionService:
    # Preserve the credential-specific rolling request allowance across research runs.
    companies_house = CompaniesHouseProvider(http, clock, companies_house_key)
    certificates = CertificateTransparencyProvider(http, clock, certificate_transparency_key)

    def providers(query: ResearchQuery) -> list[ResearchProvider]:
        if query.focus in (ResearchFocus.DOCUMENT, ResearchFocus.MEDIA):
            # Analysing a private upload does not send its extracted terms to public feeds.
            return []
        selected: list[ResearchProvider] = []
        if query.focus == ResearchFocus.COMPANY:
            selected.extend(
                (
                    SecSubmissionsProvider(http, clock),
                    SecCompanyDirectoryProvider(http, clock),
                    companies_house,
                )
            )
        elif query.focus == ResearchFocus.DOMAIN:
            selected.extend((RdapResearchProvider(http, clock), certificates))
            dns_types = ("A", "AAAA", "MX", "NS") if query.mode is ResearchMode.DETAILED else ("A",)
            selected.extend(DnsResearchProvider(http, clock, kind) for kind in dns_types)
        if GOOGLE_NEWS_SPEC.id not in disabled:
            selected.extend(
                GoogleNewsResearchProvider(http, clock, language)
                for language in dict.fromkeys(query.languages)
            )
        selected.extend(
            SocialFeedResearchProvider(http, clock, seed)
            for seed in SOCIAL_SEEDS
            if seed.spec.id not in disabled
        )
        return [provider for provider in selected if provider.id not in disabled]

    def challenge_providers(query: ResearchQuery) -> list[ResearchProvider]:
        if query.focus in (ResearchFocus.DOCUMENT, ResearchFocus.MEDIA):
            return []
        # Registry/DNS snapshots ignore contrary search terms. Re-fetching them
        # for every judgement would exhaust the challenge budget without searching.
        return providers(replace(query, focus=ResearchFocus.GENERAL))

    return ResearchCollectionService(providers, challenge_providers=challenge_providers)


def private_research_store() -> InMemoryEventStore:
    return InMemoryEventStore(memory_budget_bytes=8 * 1024 * 1024)
