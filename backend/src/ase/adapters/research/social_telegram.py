"""One aggregated research route over the curated Telegram channels.

The catalogue is bounded, so the whole curated set is a single research provider rather
than one provider per channel. The provider port allows one HTTP request per collection,
so a request reads exactly one channel preview: the curated channel whose declared
language and subject best fit the supplied phrases. That is a deliberate, disclosed
limitation, not a Telegram-wide search.

Everything collected here is a participant's claim. Items come back at the research floor
(reliability F, credibility 6) with the channel's viewpoint tags attached, and the
receipt says plainly what was and was not searched.
"""

from __future__ import annotations

from datetime import datetime

from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.feeds.telegram import GRADE_RATIONALE, channel_spec
from ase.adapters.feeds.telegram_channels import TELEGRAM_CHANNELS, TelegramChannel
from ase.adapters.feeds.telegram_preview import (
    MAX_EXCERPT_CHARS,
    TelegramPost,
    parse_channel_preview,
)
from ase.adapters.research.feed import receipt, search_terms
from ase.application.ports import Clock
from ase.domain.events import (
    Category,
    Credibility,
    Event,
    GeoConfidence,
    Reliability,
    content_hash,
    event_id,
    freeze_attributes,
)
from ase.domain.languages import matching_text
from ase.domain.research import CollectionStatus, ResearchBatch, ResearchQuery

PROVIDER_ID = "research_social_telegram"
PROVIDER_NAME = "Curated Telegram channels"
MAX_ITEMS = 20
LIMITATIONS = (
    "One curated public Telegram channel preview per request, chosen from the registry by "
    "declared language and subject fit; this is not a Telegram search, a channel-wide "
    "archive or a survey of the curated set. At most the 20 most recent posts on that "
    "preview page are checked for a supplied phrase and a post time inside the requested "
    "interval. Text excerpts only: media, replies, forwards and linked pages are never "
    "fetched. Every curated channel is a government, a state outlet, an aligned "
    "commentator or an unassessed publisher, so a match is a participant's claim and "
    "never corroboration."
)
UNAVAILABLE = (
    "The channel preview could not be retrieved or recognised, so no coverage was "
    "established. Posts are never inferred from an unrecognised page."
)


def _haystack(entry: TelegramChannel) -> str:
    return " ".join(
        (entry.name, entry.operator, entry.topic.replace("_", " "), entry.alignment, entry.reason)
    ).casefold()


class TelegramResearchProvider:
    """The curated Telegram set as one catalogue entry, reading one channel per request."""

    supports_planned_terms = True

    def __init__(
        self,
        http: FeedHttpClient,
        clock: Clock,
        channels: tuple[TelegramChannel, ...] = TELEGRAM_CHANNELS,
    ) -> None:
        if not channels:
            raise ValueError("Telegram research requires at least one curated channel")
        self._http = http
        self._clock = clock
        self._channels = channels

    @property
    def id(self) -> str:
        return PROVIDER_ID

    @property
    def name(self) -> str:
        return PROVIDER_NAME

    @property
    def language(self) -> str:
        return "und"

    @property
    def temporal_scope(self) -> str:
        return (
            "The recent posts shown on one channel preview page, filtered by post time; "
            "not a channel archive."
        )

    def supports(self, query: ResearchQuery) -> bool:
        return bool(search_terms(query)) and self._select(query) is not None

    def _select(self, query: ResearchQuery) -> TelegramChannel | None:
        """Deterministic: declared language first, then phrase overlap, then registry order."""
        languages = {language.casefold() for language in query.languages}
        eligible = [
            entry for entry in self._channels if entry.language.casefold() in languages | {"und"}
        ]
        if not eligible:
            return None
        terms = [term.casefold() for term in search_terms(query)]
        return max(
            enumerate(eligible),
            key=lambda row: (
                sum(term in _haystack(row[1]) for term in terms),
                -row[0],
            ),
        )[1]

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        entry = self._select(query)
        if entry is None or not search_terms(query):
            return receipt(
                self.id,
                self.name,
                self.language,
                CollectionStatus.UNSUPPORTED,
                "No curated Telegram channel declares a selected language, or bounded "
                "explicit terms are missing. No request was made.",
            )
        spec = channel_spec(entry)
        try:
            document = await self._http.get_text(spec.url, conditional=False, max_redirects=0)
            preview = parse_channel_preview(document, entry.username)
        except TimeoutError:
            return self._receipt(entry, CollectionStatus.TIMED_OUT, "The request timed out.")
        except Exception:
            # Upstream text can echo request detail; never surface it.
            return self._receipt(entry, CollectionStatus.FAILED, UNAVAILABLE)
        items = self._match(entry, preview.posts, query)
        status = CollectionStatus.COMPLETED if items else CollectionStatus.EMPTY
        return self._receipt(entry, status, LIMITATIONS, items)

    def _receipt(
        self,
        entry: TelegramChannel,
        status: CollectionStatus,
        explanation: str,
        items: tuple[Event, ...] = (),
    ) -> ResearchBatch:
        return receipt(
            self.id,
            f"{self.name}: @{entry.username}",
            entry.language,
            status,
            explanation,
            items,
        )

    def _match(
        self, entry: TelegramChannel, posts: tuple[TelegramPost, ...], query: ResearchQuery
    ) -> tuple[Event, ...]:
        terms = [matching_text(term, entry.language) for term in search_terms(query)]
        now = self._clock.now()
        matched: list[Event] = []
        for post in posts[:MAX_ITEMS]:
            if post.published_at is None or not query.since <= post.published_at < query.until:
                continue
            if not any(term in matching_text(post.text, entry.language) for term in terms):
                continue
            matched.append(self._to_event(entry, post, now))
        return tuple(matched)

    def _to_event(self, entry: TelegramChannel, post: TelegramPost, now: datetime) -> Event:
        return Event(
            id=event_id(self.id, post.key),
            source_id=self.id,
            category=Category.SOCIAL,
            subtype="post",
            title=post.text[:140],
            summary=post.text[:MAX_EXCERPT_CHARS],
            url=post.url,
            published_at=post.published_at,
            observed_at=now,
            geo_confidence=GeoConfidence.NONE,
            country_iso=None,
            language=entry.language,
            tags=frozenset({"telegram", entry.topic, *entry.viewpoint_tags}),
            severity=None,
            reliability=Reliability.F,
            credibility=Credibility.CANNOT_BE_JUDGED,
            grade_rationale=GRADE_RATIONALE,
            attributes=freeze_attributes(
                {
                    "original_account": f"@{entry.username}",
                    "original_account_url": f"https://t.me/{entry.username}",
                    "original_publisher": entry.operator,
                    "collection_feed": f"{PROVIDER_NAME}: @{entry.username}",
                    "viewpoint": entry.viewpoint,
                    "alignment": entry.alignment or None,
                    "provenance_status": "unverified",
                    "language_basis": "configured channel language; not independently detected",
                    "excerpt_only": True,
                    "media": 0,
                }
            ),
            content_hash=content_hash(post.key, post.text[:200]),
        )
