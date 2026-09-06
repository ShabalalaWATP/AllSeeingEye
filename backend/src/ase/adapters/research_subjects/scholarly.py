"""Metadata-only scholarly searches, with provider-reported update signals.

Primary API contracts: https://help.openalex.org/data/works/attributes/
https://help.openalex.org/api/authentication/ (keyless basic queries, August 2026).
https://www.crossref.org/documentation/retrieve-metadata/retraction-watch/
https://www.crossref.org/documentation/retrieve-metadata/rest-api/rest-api-filters/
"""

import re
from datetime import UTC
from typing import Any
from urllib.parse import quote, urlencode

from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.research.feed import search_terms
from ase.adapters.research_records.records import collect_json, receipt, text
from ase.adapters.research_subjects.events import subject_event as record_event
from ase.adapters.research_subjects.selection import day, doi, in_window, selected
from ase.application.ports import Clock
from ase.domain.events import Category, Event
from ase.domain.research import CollectionStatus, ResearchBatch, ResearchQuery


class OpenAlexProvider:
    id = "research-openalex"
    name = "OpenAlex scholarly metadata"
    temporal_scope = (
        "First 20 dated publication metadata matches; no complete historical or integrity coverage."
    )

    def __init__(self, http: FeedHttpClient, clock: Clock) -> None:
        self.http, self.clock = http, clock

    def supports(self, query: ResearchQuery) -> bool:
        return selected(query, self.id, "academic:") and query.country_iso is None

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        if not self.supports(query):
            return receipt(
                self.id,
                self.name,
                CollectionStatus.UNSUPPORTED,
                "Select scholarly metadata with English search terms and no country filter.",
            )
        url = "https://api.openalex.org/works?" + urlencode(
            {
                "search": " ".join(search_terms(query)),
                "per_page": 20,
                "page": 1,
                "filter": f"from_publication_date:{query.since.astimezone(UTC).date()},"
                f"to_publication_date:{query.until.astimezone(UTC).date()}",
                "select": "id,doi,display_name,publication_date,is_retracted,type,language",
            }
        )
        return await collect_json(
            self.http,
            self.id,
            self.name,
            url,
            lambda data: self.parse(data, query),
            "First 20 scholarly metadata matches, exact date-window filtering. "
            "No papers or abstracts fetched. Retraction flags are provider reports, "
            "not independent verdicts; missing flags remain unknown. "
            "Metadata language and topic relevance require review. Anonymous API limits apply.",
        )

    def parse(self, data: dict[str, Any], query: ResearchQuery) -> list[Event]:
        rows = data.get("results")
        if not isinstance(rows, list):
            raise ValueError("Missing scholarly results")
        result, seen = [], set()
        for row in rows[:20]:
            if not isinstance(row, dict):
                continue
            identity = text(row.get("id"), 100)
            if not re.fullmatch(r"https://openalex.org/W[0-9]{1,20}", identity) or identity in seen:
                continue
            published, title = day(row.get("publication_date")), text(row.get("display_name"))
            if not title or not in_window(published, query):
                continue
            seen.add(identity)
            retracted = row.get("is_retracted")
            signal = (
                "reported"
                if retracted is True
                else "not_reported"
                if retracted is False
                else "unknown"
            )
            identifier = doi(row.get("doi"))
            result.append(
                record_event(
                    self.id,
                    identity,
                    title,
                    f"OpenAlex scholarly metadata. DOI: {identifier or 'not recorded'}. "
                    f"Retraction signal: {signal}. "
                    "A missing or false flag does not establish integrity. "
                    "The work was not examined; publication date has day precision.",
                    identity,
                    self.clock.now(),
                    category=Category.NEWS,
                    published=published,
                    attributes={
                        "record_kind": "scholarly_metadata",
                        "doi": identifier,
                        "retraction_signal": signal,
                        "signal_provider": "OpenAlex",
                        "date_precision": "day",
                        "work_type": text(row.get("type"), 60),
                    },
                )
            )
        return result


class CrossrefProvider:
    id = "research-crossref"
    name = "Crossref scholarly metadata"
    temporal_scope = (
        "First 20 dated publication metadata matches; no complete historical or retraction search."
    )

    def __init__(self, http: FeedHttpClient, clock: Clock) -> None:
        self.http, self.clock = http, clock

    def supports(self, query: ResearchQuery) -> bool:
        return selected(query, self.id, "academic:") and query.country_iso is None

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        if not self.supports(query):
            return receipt(
                self.id,
                self.name,
                CollectionStatus.UNSUPPORTED,
                "Select scholarly metadata with English search terms and no country filter.",
            )
        url = "https://api.crossref.org/works?" + urlencode(
            {
                "query.bibliographic": " ".join(search_terms(query)),
                "rows": 20,
                "offset": 0,
                "filter": f"from-pub-date:{query.since.astimezone(UTC).date()},"
                f"until-pub-date:{query.until.astimezone(UTC).date()}",
            }
        )
        return await collect_json(
            self.http,
            self.id,
            self.name,
            url,
            lambda data: self.parse(data, query),
            "First 20 Crossref metadata matches; incomplete publication dates excluded. "
            "Update-to links describe notices about a target DOI, not necessarily "
            "retraction of the returned record. No notice, article, full text or "
            "complete retraction search was fetched. Language/topic relevance require review.",
        )

    def parse(self, data: dict[str, Any], query: ResearchQuery) -> list[Event]:
        message = data.get("message")
        rows = message.get("items") if isinstance(message, dict) else None
        if not isinstance(rows, list):
            raise ValueError("Missing scholarly results")
        result, seen = [], set()
        for row in rows[:20]:
            if not isinstance(row, dict):
                continue
            identity = doi(row.get("DOI"))
            titles = row.get("title")
            title = text(titles[0]) if isinstance(titles, list) and titles else ""
            published = row.get("published")
            parts = published.get("date-parts") if isinstance(published, dict) else None
            fields = parts[0] if isinstance(parts, list) and parts else None
            date = (
                day("-".join(f"{n:02d}" if i else f"{n:04d}" for i, n in enumerate(fields)))
                if (
                    isinstance(fields, list)
                    and len(fields) == 3
                    and all(type(n) is int for n in fields)
                )
                else None
            )
            if not identity or identity in seen or not title or not in_window(date, query):
                continue
            seen.add(identity)
            updates = row.get("update-to")
            notices = []
            for update in updates[:10] if isinstance(updates, list) else []:
                if isinstance(update, dict) and (target := doi(update.get("DOI"))):
                    notices.append(
                        f"{text(update.get('type'), 40)} notice targets {target} "
                        f"(reported by {text(update.get('source'), 40) or 'unknown'})"
                    )
            signals = (
                "; ".join(notices)
                or "No update-to signal in this returned metadata; integrity unknown."
            )
            result.append(
                record_event(
                    self.id,
                    identity,
                    title,
                    f"Crossref metadata for DOI {identity}. {signals}. "
                    "A notice's target DOI is distinct from the notice DOI. "
                    "No integrity verdict is inferred.",
                    "https://doi.org/" + quote(identity, safe="/"),
                    self.clock.now(),
                    category=Category.NEWS,
                    published=date,
                    attributes={
                        "record_kind": "scholarly_metadata",
                        "doi": identity,
                        "update_signals": signals[:1800],
                        "date_precision": "day",
                        "retraction_status": "not_determined",
                    },
                )
            )
        return result
