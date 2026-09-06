"""On-demand matching within configured public social RSS/Atom feeds, without scraping."""

from dataclasses import replace

from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.feeds.rss_seeds import RssSeed
from ase.adapters.research.feed import collect_feed, receipt, search_terms
from ase.application.ports import Clock
from ase.domain.events import Category, Reliability
from ase.domain.research import CollectionStatus, ResearchBatch, ResearchQuery
from ase.domain.sources import SourceKind

LIMITATIONS = (
    "Configured public RSS/Atom feed only, not a platform-wide search or historical archive. "
    "At most the first 200 items are checked for a supplied phrase in headline/feed text and "
    "a publication date in the requested interval; undated items are excluded. Feed language "
    "is configured, not detected. Account labels do not verify identity or reliability. "
    "Geographic relevance is not guaranteed; linked posts, media and replies are not fetched."
)


class SocialFeedResearchProvider:
    def __init__(self, http: FeedHttpClient, clock: Clock, seed: RssSeed) -> None:
        if seed.spec.category is not Category.SOCIAL or seed.spec.kind is not SourceKind.RSS:
            raise ValueError("Social research requires a configured social RSS/Atom feed")
        if len(seed.spec.id) > 100 or len(seed.spec.name) > 180:
            raise ValueError("Social feed identity exceeds research receipt bounds")
        self._http = http
        self._clock = clock
        self._seed = seed

    @property
    def id(self) -> str:
        return f"research_social_{self._seed.spec.id}"

    @property
    def name(self) -> str:
        return self._seed.spec.name

    def supports(self, query: ResearchQuery) -> bool:
        return bool(search_terms(query)) and (
            self._seed.spec.language.lower() in {language.lower() for language in query.languages}
            or self._seed.spec.language == "und"
        )

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        if not self.supports(query):
            return receipt(
                self.id,
                self.name,
                self._seed.spec.language,
                CollectionStatus.UNSUPPORTED,
                "This configured feed language is not selected, or bounded explicit terms are "
                "missing (maximum 1000 combined characters). No request was made.",
            )
        spec = replace(self._seed.spec, id=self.id, reliability=Reliability.F, organisation="")
        return await collect_feed(
            self._http,
            self._clock,
            replace(self._seed, spec=spec),
            query,
            LIMITATIONS,
            local_match=True,
        )
