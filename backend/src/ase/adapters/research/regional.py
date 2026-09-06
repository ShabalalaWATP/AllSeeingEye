"""Private on-demand matching of verified public regional publisher feeds."""

from dataclasses import replace

from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.feeds.rss_seeds import RssSeed
from ase.adapters.research.feed import collect_feed, receipt, search_terms
from ase.application.ports import Clock
from ase.domain.events import Reliability
from ase.domain.research import CollectionStatus, ResearchBatch, ResearchQuery

REGIONAL_COUNTRIES = {
    "meduza_ru": "RU",
    "mediazona_ru": "RU",
    "insider_ru": "RU",
    "cdt_zh": "CN",
    "hrana_fa": "IR",
    "hrana_en": "IR",
    "iranwire_fa": "IR",
    "iranwire_en": "IR",
}
LANGUAGE_ALIASES = {"zh": frozenset({"zh", "zh-cn", "zh-hans"})}
LIMITATIONS = (
    "Publisher-supplied public feed, not a full historical or regional search. "
    "At most 200 feed items are checked; IranWire selects the newest 200. "
    "Only headline, date, attribution and source link are retained. "
    "Explicit phrases must match a headline and publication date must fall in the "
    "requested interval; undated items are excluded. The regional preset routes feeds "
    "but does not establish incident geography. Language is configured, not detected. "
    "Editions share publisher origin; source reliability and claims remain unassessed."
)


class RegionalFeedResearchProvider:
    def __init__(self, http: FeedHttpClient, clock: Clock, seed: RssSeed) -> None:
        if seed.spec.id not in REGIONAL_COUNTRIES or not seed.options.headlines_only:
            raise ValueError("Regional research requires an approved headline-only seed")
        self._http, self._clock, self._seed = http, clock, seed

    @property
    def id(self) -> str:
        return f"research_regional_{self._seed.spec.id}"

    @property
    def name(self) -> str:
        return self._seed.spec.name

    @property
    def language(self) -> str:
        return self._seed.spec.language

    @property
    def query_language_aliases(self) -> tuple[str, ...]:
        return tuple(sorted(LANGUAGE_ALIASES.get(self.language, frozenset({self.language}))))

    @property
    def temporal_scope(self) -> str:
        return (
            "Recent RSS snapshot filtered by publication date; not a complete historical archive."
        )

    def supports(self, query: ResearchQuery) -> bool:
        languages = LANGUAGE_ALIASES.get(
            self._seed.spec.language, frozenset({self._seed.spec.language})
        )
        explicit = query.source_ids is not None and self.id in query.source_ids
        region = (
            query.country_iso is None
            or query.country_iso.upper() == REGIONAL_COUNTRIES[self._seed.spec.id]
        )
        return (
            bool(search_terms(query))
            and bool(languages.intersection(query.languages))
            and (region or explicit)
        )

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        if not self.supports(query):
            return receipt(
                self.id,
                self.name,
                self._seed.spec.language,
                CollectionStatus.UNSUPPORTED,
                "The feed language or regional routing does not match, or bounded explicit "
                "phrases are missing. No request was made.",
            )
        spec = replace(self._seed.spec, id=self.id, reliability=Reliability.F)
        return await collect_feed(
            self._http,
            self._clock,
            replace(self._seed, spec=spec),
            query,
            LIMITATIONS,
            local_match=True,
        )
