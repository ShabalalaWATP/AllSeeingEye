"""Additional live headline sources, separate from the bounded private provider inventory."""

from ase.adapters.feeds.rss_seeds_uk_news import UK_NEWS_SEEDS
from ase.adapters.feeds.rss_seeds_world_news import WORLD_NEWS_SEEDS

NEWS_SEEDS = UK_NEWS_SEEDS + WORLD_NEWS_SEEDS
