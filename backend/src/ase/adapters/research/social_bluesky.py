"""One aggregated research route over the curated Bluesky accounts.

The whole registry is exposed through a single capability rather than one provider per
account, so the bounded research catalogue does not grow with the watch list. An admitted
collection task reads at most `MAX_ACCOUNTS` curated author feeds, chosen by the topics
the supplied phrases mention, and returns one coverage receipt for the task. That bounded
fan-out is disclosed in the receipt, the capability constraints and the source catalogue;
nothing else is fetched, and linked pages, media and quoted posts are never followed.
"""

from dataclasses import replace
from typing import Any, Final

from ase.adapters.feeds.bluesky import POSTS_PER_ACCOUNT, SPEC, author_feed_url
from ase.adapters.feeds.bluesky_accounts import ACCOUNTS, BlueskyAccount
from ase.adapters.feeds.bluesky_posts import to_event
from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.research.feed import receipt, search_terms
from ase.application.ports import Clock
from ase.application.ports.research_capabilities import ProviderCapabilities
from ase.domain.events import Event, Reliability
from ase.domain.languages import matching_text
from ase.domain.research import CollectionStatus, ResearchBatch, ResearchQuery

PROVIDER_ID: Final = "research_social_bluesky"
PROVIDER_NAME: Final = "Bluesky curated accounts research"
MAX_ACCOUNTS: Final = 3
MAX_ITEMS: Final = 60
RATIONALE: Final = (
    "Public account post collected on demand; the account, its claims and any linked "
    "material remain unassessed."
)
LIMITATIONS: Final = (
    "Curated public Bluesky author feeds only, not a platform-wide search: "
    "`app.bsky.feed.searchPosts` refuses unauthenticated callers and is not used. One "
    "admitted task reads at most three reviewed accounts and the most recent posts of "
    "each, keeping dated posts inside the requested interval that contain a supplied "
    "phrase. Reposts are excluded and replies outside the author's own thread never "
    "arrive. Account labels do not verify identity, and a curated topic is not evidence "
    "of geography; linked pages, media and quoted posts are not fetched."
)
# Registry topics that a phrase can select, with the words that select them.
TOPIC_WORDS: Final[dict[str, tuple[str, ...]]] = {
    "ukraine_russia": ("ukraine", "ukrainian", "russia", "russian", "kyiv", "moscow", "kherson"),
    "china_taiwan": ("china", "chinese", "taiwan", "taiwanese", "beijing", "hong kong"),
    "indo_pacific": ("indo-pacific", "japan", "philippines", "australia", "asean", "korea sea"),
    "middle_east": ("israel", "gaza", "iran", "lebanon", "syria", "yemen", "houthi", "hezbollah"),
    "korea": ("north korea", "pyongyang", "dprk", "south korea", "seoul"),
    "south_asia": ("india", "pakistan", "kashmir", "afghanistan", "bangladesh", "delhi"),
    "africa": ("africa", "sahel", "sudan", "somalia", "ethiopia", "nigeria", "congo", "mali"),
    "latin_america": ("latin america", "mexico", "venezuela", "colombia", "brazil", "cartel"),
    "finance_markets": ("market", "inflation", "interest rate", "bank", "sanctions", "economy"),
    "cyber_threat_intel": ("cyber", "ransomware", "malware", "vulnerability", "hacking", "breach"),
    "drones_uncrewed": ("drone", "drones", "uav", "uncrewed", "unmanned", "loitering"),
    "defence_analysis": ("military", "defence", "defense", "missile", "army", "navy", "weapons"),
    "security_policy": ("nato", "strategy", "deterrence", "arms control", "security policy"),
    "world_leaders": ("european commission", "government", "summit", "president", "parliament"),
    "maritime_aviation": ("ship", "vessel", "shipping", "aircraft", "airspace", "flight", "naval"),
    "space": ("space", "satellite", "launch", "orbit", "rocket", "spacecraft"),
    "energy": ("energy", "oil", "gas", "electricity", "pipeline", "nuclear power", "grid"),
    "humanitarian": ("humanitarian", "refugee", "displacement", "famine", "aid", "outbreak"),
    "disinformation": ("disinformation", "propaganda", "influence operation", "fact check"),
    "global_news": (),  # the default fallback, never selected by a word
}


def selected_accounts(
    terms: tuple[str, ...], accounts: tuple[BlueskyAccount, ...] = ACCOUNTS
) -> tuple[BlueskyAccount, ...]:
    """Pick at most `MAX_ACCOUNTS` curated accounts whose topic the phrases mention."""
    haystack = " ".join(term.lower() for term in terms)
    topics = [
        topic for topic, words in TOPIC_WORDS.items() if any(word in haystack for word in words)
    ]
    ordered = [account for topic in topics for account in accounts if account.topic == topic]
    if not ordered:
        ordered = [account for account in accounts if account.topic == "global_news"]
    return tuple(ordered[:MAX_ACCOUNTS])


class BlueskyResearchProvider:
    supports_planned_terms = True

    id = PROVIDER_ID
    name = PROVIDER_NAME
    language = "und"
    temporal_scope = (
        "Recent author-feed snapshots filtered by post time; not a complete archive of an "
        "account and not a platform-wide history."
    )

    def __init__(
        self,
        http: FeedHttpClient,
        clock: Clock,
        accounts: tuple[BlueskyAccount, ...] = ACCOUNTS,
    ) -> None:
        if not accounts:
            raise ValueError("Bluesky research requires reviewed accounts")
        self._http, self._clock, self._accounts = http, clock, accounts
        # Research items carry this route's identity and an unassessed grade, never the
        # live feed's source identity.
        self._spec = replace(SPEC, id=self.id, reliability=Reliability.F, organisation="")

    def supports(self, query: ResearchQuery) -> bool:
        return bool(search_terms(query))

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        terms = search_terms(query)
        if not terms:
            return receipt(
                self.id,
                self.name,
                self.language,
                CollectionStatus.UNSUPPORTED,
                "Bounded explicit phrases are required (maximum 1000 combined characters). "
                "No request was made.",
            )
        accounts = selected_accounts(terms, self._accounts)
        items: dict[str, Event] = {}
        failures = 0
        for account in accounts:
            payload = await self._read(account)
            if payload is None:
                failures += 1
                continue
            for event in self._matching(payload, account, terms, query):
                items.setdefault(event.id, event)
        if failures == len(accounts):
            return receipt(
                self.id,
                self.name,
                self.language,
                CollectionStatus.FAILED,
                "The curated Bluesky accounts could not be read; no coverage was established.",
            )
        found = tuple(items.values())[:MAX_ITEMS]
        status = CollectionStatus.COMPLETED if found else CollectionStatus.EMPTY
        return receipt(self.id, self.name, self.language, status, LIMITATIONS, found)

    async def _read(self, account: BlueskyAccount) -> Any | None:
        try:
            return await self._http.get_json(
                author_feed_url(account.handle, POSTS_PER_ACCOUNT), conditional=False
            )
        except Exception:
            # Upstream errors can carry request text; never surface them in a receipt.
            return None

    def _matching(
        self,
        payload: Any,
        account: BlueskyAccount,
        terms: tuple[str, ...],
        query: ResearchQuery,
    ) -> list[Event]:
        feed = payload.get("feed") if isinstance(payload, dict) else None
        if not isinstance(feed, list):
            return []
        now = self._clock.now()
        found: list[Event] = []
        for item in feed[:MAX_ITEMS]:
            event = to_event(item, account, self._spec, now)
            if event is None or event.published_at is None:
                continue
            if not query.since <= event.published_at < query.until:
                continue
            text = matching_text(f"{event.title} {event.summary or ''}", event.language)
            if not any(matching_text(term, event.language) in text for term in terms):
                continue
            found.append(replace(event, grade_rationale=RATIONALE))
        return found

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            language=self.language,
            supports_planned_terms=self.supports_planned_terms,
            temporal_scope=self.temporal_scope,
        )
