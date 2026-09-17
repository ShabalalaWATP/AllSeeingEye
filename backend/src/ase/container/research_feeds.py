"""Interleave source families without changing the collection request budget."""

from itertools import zip_longest

from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.feeds.rss_seeds_cyber import CYBER_SEEDS
from ase.adapters.feeds.rss_seeds_economy import ECONOMY_SEEDS
from ase.adapters.feeds.rss_seeds_official import OFFICIAL_SEEDS
from ase.adapters.feeds.rss_seeds_outlets import OUTLET_SEEDS
from ase.adapters.feeds.rss_seeds_regional import REGIONAL_SEEDS
from ase.adapters.research.publisher import PublisherFeedResearchProvider
from ase.adapters.research.regional import RegionalFeedResearchProvider
from ase.adapters.research.social_bluesky import BlueskyResearchProvider
from ase.adapters.research.social_telegram import TelegramResearchProvider
from ase.application.ports import Clock
from ase.application.ports.research import ResearchProvider


def public_research_feeds(
    http: FeedHttpClient, clock: Clock, *, spatial: bool
) -> list[ResearchProvider]:
    regional: list[ResearchProvider] = [
        RegionalFeedResearchProvider(http, clock, seed) for seed in REGIONAL_SEEDS
    ]
    # Each curated platform set is one aggregated route, never one per channel or account.
    social: list[ResearchProvider] = [
        TelegramResearchProvider(http, clock),
        BlueskyResearchProvider(http, clock),
    ]
    if spatial:
        # Existing unsupported capabilities explain the spatial boundary. The new
        # publisher family has no spatial support and does not enlarge this plan.
        return [*regional, *social]
    official: list[ResearchProvider] = [
        PublisherFeedResearchProvider(http, clock, seed) for seed in OFFICIAL_SEEDS
    ]
    outlets: list[ResearchProvider] = [
        PublisherFeedResearchProvider(http, clock, seed) for seed in OUTLET_SEEDS
    ]
    economic: list[ResearchProvider] = [
        PublisherFeedResearchProvider(http, clock, seed) for seed in ECONOMY_SEEDS
    ]
    cyber: list[ResearchProvider] = [
        PublisherFeedResearchProvider(http, clock, seed) for seed in CYBER_SEEDS
    ]
    # A short request budget should not be consumed by one entire feed family
    # before another is considered. Unsupported languages consume no requests.
    # The curated platform sets are two routes, so they interleave like any other family.
    return [
        provider
        for group in zip_longest(official, outlets, regional, economic, cyber, social)
        for provider in group
        if provider is not None
    ]
