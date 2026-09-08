"""Single-request RSS collection with strict dates and conservative provenance."""

from dataclasses import replace
from datetime import datetime
from urllib.parse import urlsplit

# Element is an annotation type; untrusted XML is parsed with defusedxml below.
# nosemgrep: python.lang.security.use-defused-xml.use-defused-xml
from xml.etree.ElementTree import Element  # nosec B405

from defusedxml.ElementTree import fromstring

from ase.adapters.feeds.http import FeedHttpClient, is_public_address
from ase.adapters.feeds.rss import (
    MAX_ITEMS,
    RssConnector,
    child_text,
    children,
    select_feed_items,
)
from ase.adapters.feeds.rss_seeds import RssSeed
from ase.application.feeds.pipeline import strip_html
from ase.application.ports import Clock
from ase.domain.events import (
    MAX_SUMMARY,
    MAX_TITLE,
    Credibility,
    Event,
    Reliability,
    freeze_attributes,
)
from ase.domain.languages import matching_text
from ase.domain.research import CollectionAttempt, CollectionStatus, ResearchBatch, ResearchQuery


def search_terms(query: ResearchQuery) -> tuple[str, ...]:
    """Only explicit supplied phrases go upstream, never the private question itself."""
    terms = tuple(" ".join(term.replace('"', " ").split()) for term in query.terms)
    if not terms or any(not term for term in terms) or sum(map(len, terms)) > 1000:
        return ()
    return terms


def web_url(value: str) -> str | None:
    try:
        parts = urlsplit(value)
        if (
            len(value) > 2000
            or parts.scheme not in {"http", "https"}
            or not parts.hostname
            or parts.username
            or parts.password
            or not is_public_address(parts.hostname)
        ):
            return None
        return value
    except ValueError:
        return None


def receipt(
    source_id: str,
    name: str,
    language: str,
    status: CollectionStatus,
    explanation: str,
    items: tuple[Event, ...] = (),
) -> ResearchBatch:
    return ResearchBatch(
        items,
        (CollectionAttempt(source_id, name, status, len(items), explanation, language),),
    )


class ResearchFeedParser(RssConnector):
    """Reuse the shared RSS mapping, excluding undated items instead of inventing dates."""

    def parse(self, text: str, query: ResearchQuery, *, local_match: bool) -> tuple[Event, ...]:
        root = fromstring(text.lstrip("\ufeff").encode("utf-8"))
        if root.tag.rsplit("}", 1)[-1].lower() not in {"rss", "rdf", "feed"}:
            raise ValueError("Response is not an RSS or Atom feed")
        terms = search_terms(query)
        events: dict[str, Event] = {}
        now = self._clock.now()
        selected, count = select_feed_items(root, newest_first=self._options.newest_first)
        for item in selected:
            event = self._to_event(item, now)
            if event is None or event.published_at is None:
                continue
            if not query.since <= event.published_at < query.until:
                continue
            if local_match and not any(
                matching_text(term, event.language)
                in matching_text(f"{event.title} {event.summary or ''}", event.language)
                for term in terms
            ):
                continue
            if count > MAX_ITEMS:
                event = replace(
                    event,
                    attributes=freeze_attributes(
                        {
                            **event.attributes,
                            "feed_items_available": count,
                            "feed_items_limit": MAX_ITEMS,
                            "feed_items_truncated": True,
                        }
                    ),
                )
            events[event.id] = event
        return tuple(events.values())

    def _to_event(self, item: Element, now: datetime) -> Event | None:
        event = super()._to_event(item, now)
        if event is None:
            return None
        sources = children(item, "source")
        publisher = child_text(item, "source") or None
        publisher_url = web_url(sources[0].get("url", "")) if sources else None
        authors = children(item, "author")
        account = child_text(authors[0], "name") if authors else ""
        account_url = web_url(child_text(authors[0], "uri")) if authors else None
        attributes = dict(event.attributes)
        attributes.update(
            {
                "original_publisher": publisher,
                "original_publisher_url": publisher_url,
                "original_account": account or attributes.get("author"),
                "original_account_url": account_url,
                "collection_feed": self.spec.name,
                "provenance_status": "unverified",
                "language_basis": "configured feed or edition; not independently detected",
            }
        )
        return replace(
            event,
            title=(strip_html(event.title) or "")[:MAX_TITLE],
            summary=(event.summary or "")[:MAX_SUMMARY] or None,
            url=web_url(event.url or ""),
            reliability=Reliability.F,
            credibility=Credibility.CANNOT_BE_JUDGED,
            grade_rationale="Publisher or account reliability and information are unassessed",
            attributes=freeze_attributes(attributes),
        )


async def collect_feed(
    http: FeedHttpClient,
    clock: Clock,
    seed: RssSeed,
    query: ResearchQuery,
    explanation: str,
    *,
    local_match: bool = False,
) -> ResearchBatch:
    spec = seed.spec
    try:
        text = await http.get_text(spec.url, conditional=False, max_redirects=0)
        items = ResearchFeedParser(http, clock, spec, seed.options).parse(
            text, query, local_match=local_match
        )
    except TimeoutError:
        return receipt(
            spec.id,
            spec.name,
            spec.language,
            CollectionStatus.TIMED_OUT,
            "The public feed request exceeded its time limit.",
        )
    except Exception:
        # Feed errors can embed URLs with private query terms. Never expose their text.
        return receipt(
            spec.id,
            spec.name,
            spec.language,
            CollectionStatus.FAILED,
            "The public feed could not be retrieved or parsed; no coverage was established.",
        )
    status = CollectionStatus.COMPLETED if items else CollectionStatus.EMPTY
    return receipt(spec.id, spec.name, spec.language, status, explanation, items)
