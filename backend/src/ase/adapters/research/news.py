"""Question-specific Google News RSS, using the existing undocumented free feed.

Language/region selection: https://support.google.com/googlenews/answer/9005601
That help page does not provide an RSS API guarantee. No articles are fetched.
"""

from dataclasses import replace
from datetime import UTC, date, timedelta
from urllib.parse import urlencode

from ase.adapters.feeds.google_news import OPTIONS, SEARCH_URL, SPEC
from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.feeds.rss_seeds import RssSeed
from ase.adapters.research.feed import collect_feed, receipt, search_terms
from ase.application.ports import Clock
from ase.domain.events import Reliability
from ase.domain.languages import LANGUAGES
from ase.domain.research import CollectionStatus, ResearchBatch, ResearchQuery

# Each instance represents one admitted request and one edition, not a hidden fan-out.
EDITIONS: dict[str, tuple[str, str, str]] = {
    language.code.lower(): (edition.hl, edition.gl, edition.ceid)
    for language in LANGUAGES
    if (edition := language.google_news_edition) is not None
}
LIMITATIONS = (
    "Undocumented Google News RSS search; availability and completeness are not guaranteed. "
    "Only the first 200 feed items are considered; dated items in the requested UTC interval "
    "are retained. Edition selection does not verify article language or geographic relevance. "
    "Supplied phrases are not automatically translated. Publisher/account claims remain "
    "unverified; no full articles or linked pages are fetched."
)


class GoogleNewsResearchProvider:
    supports_planned_terms = True

    temporal_scope = (
        "Bounded RSS search results filtered by publication date; date operators do not "
        "establish a complete historical archive or event-time coverage."
    )

    def __init__(self, http: FeedHttpClient, clock: Clock, language: str = "en") -> None:
        if (
            not language
            or len(language) > 16
            or not all(char.isascii() and (char.isalnum() or char == "-") for char in language)
        ):
            raise ValueError("Invalid research language")
        self.language = language.lower()
        self._http = http
        self._clock = clock

    @property
    def id(self) -> str:
        return f"research_google_news_{self.language}"

    @property
    def name(self) -> str:
        return f"Google News research ({self.language})"

    def supports(self, query: ResearchQuery) -> bool:
        return (
            self.language in EDITIONS
            and self.language in {language.lower() for language in query.languages}
            and bool(search_terms(query))
        )

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        if not self.supports(query):
            return receipt(
                self.id,
                self.name,
                self.language,
                CollectionStatus.UNSUPPORTED,
                "This edition is not selected or supported, or bounded explicit terms are missing "
                "(maximum 1000 combined characters). No request was made.",
            )
        hl, gl, ceid = EDITIONS[self.language]
        phrases = " OR ".join(f'"{term}"' for term in search_terms(query))
        # Broaden upstream calendar dates, then enforce the exact half-open UTC interval locally.
        start, end = query.since.astimezone(UTC).date(), query.until.astimezone(UTC).date()
        after = start - timedelta(days=1) if start > date.min else start
        before = end + timedelta(days=1) if end < date.max else end
        url = (
            SEARCH_URL
            + "?"
            + urlencode(
                {
                    "q": f"({phrases}) after:{after} before:{before}",
                    "hl": hl,
                    "gl": gl,
                    "ceid": ceid,
                }
            )
        )
        spec = replace(
            SPEC,
            id=self.id,
            name=self.name,
            url=url,
            language=self.language,
            reliability=Reliability.F,
            organisation="",
        )
        return await collect_feed(
            self._http, self._clock, RssSeed(spec, OPTIONS), query, LIMITATIONS
        )
