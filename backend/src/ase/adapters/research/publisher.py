"""Private headline searches of the existing official and general publisher RSS feeds."""

from dataclasses import replace

from ase.adapters.feeds.cyber_rss import cyber_publication
from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.feeds.rss_seeds import RssSeed
from ase.adapters.feeds.rss_seeds_cyber import CYBER_SEEDS
from ase.adapters.feeds.rss_seeds_economy import ECONOMY_SEEDS
from ase.adapters.feeds.rss_seeds_official import OFFICIAL_SEEDS
from ase.adapters.feeds.rss_seeds_outlets import OUTLET_SEEDS
from ase.adapters.research.feed import collect_feed, receipt, search_terms
from ase.application.ports import Clock
from ase.domain.events import freeze_attributes
from ase.domain.research import CollectionStatus, ResearchBatch, ResearchQuery

PUBLISHER_SEEDS = OFFICIAL_SEEDS + OUTLET_SEEDS + ECONOMY_SEEDS + CYBER_SEEDS
LIMITATIONS = (
    "One public publisher RSS/Atom snapshot, not a complete archive or news search. "
    "At most the first 200 items are checked. Only headline, publication date, source "
    "link and attribution metadata are retained; articles and media are not fetched. "
    "Supplied phrases are matched locally against headlines and are not sent to the "
    "publisher. Undated and out-of-interval items are excluded. Language is configured, "
    "not detected or translated. Country selection does not establish incident geography; "
    "area collection is unsupported. Copies and editions retain their publisher origin "
    "and do not establish independent corroboration. Claims remain unassessed."
)


class PublisherFeedResearchProvider:
    supports_planned_terms = True
    spatial_scope = "Publisher headlines do not establish geometry; area search is unsupported."
    temporal_scope = (
        "Recent RSS/Atom snapshot filtered by publication date; not a complete historical archive."
    )

    def __init__(self, http: FeedHttpClient, clock: Clock, seed: RssSeed) -> None:
        # Accept only the reviewed fixed seeds, never a question-supplied URL or a
        # second registration of a regional/social feed already supported elsewhere.
        if seed not in PUBLISHER_SEEDS:
            raise ValueError("Publisher research requires an approved official or outlet seed")
        self._http, self._clock, self._seed = http, clock, seed

    @property
    def id(self) -> str:
        return f"research_publisher_{self._seed.spec.id}"

    @property
    def name(self) -> str:
        return self._seed.spec.name

    @property
    def language(self) -> str:
        return self._seed.spec.language

    def supports(self, query: ResearchQuery) -> bool:
        return query.area is None and self.language in query.languages and bool(search_terms(query))

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        if not self.supports(query):
            return receipt(
                self.id,
                self.name,
                self.language,
                CollectionStatus.UNSUPPORTED,
                "Select the configured feed language and bounded explicit phrases. "
                "Publisher headlines do not support area collection. No request was made.",
            )
        original = self._seed.spec
        batch = await collect_feed(
            self._http,
            self._clock,
            replace(self._seed, options=replace(self._seed.options, headlines_only=True)),
            query,
            LIMITATIONS,
            local_match=True,
        )
        # Keep the original event identity across live/private collection so the same
        # feed item cannot become an extra record. The research source ID selects its
        # unassessed policy; its catalogue organisation must match the parent source.
        items = tuple(
            replace(
                event,
                source_id=self.id,
                attributes=freeze_attributes(
                    {
                        **event.attributes,
                        "original_source_id": original.id,
                        "original_source_organisation": original.organisation,
                        "collection_source_id": self.id,
                        "content_scope": "publisher headline and attribution metadata only",
                    }
                ),
            )
            for event in batch.items
        )
        if self._seed in CYBER_SEEDS:
            items = tuple(cyber_publication(event, original) for event in items)
        return replace(
            batch,
            items=items,
            attempts=tuple(replace(attempt, source_id=self.id) for attempt in batch.attempts),
        )
