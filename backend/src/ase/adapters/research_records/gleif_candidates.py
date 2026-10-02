"""One bounded GLEIF name request. Response links are never followed."""

from typing import Any
from urllib.parse import urlencode

from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient
from ase.adapters.research_records.gleif import ORIGIN, lei_number
from ase.application.ports.lei_candidates import LeiCandidate
from ase.domain.errors import InvalidRequest


def _text(value: Any, limit: int = 300) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError("Invalid GLEIF candidate field")
    return value.strip()


class GleifCandidates:
    def __init__(self, http: FeedHttpClient) -> None:
        self.http = http

    async def search(self, name: str, country: str | None) -> tuple[LeiCandidate, ...]:
        # GLEIF treats commas as OR separators in filters. Search the name as a
        # phrase with punctuation normalised, never as multiple alternative terms.
        params = {"filter[entity.legalName]": name.replace(",", " "), "page[size]": "10"}
        if country:
            params["filter[entity.legalAddress.country]"] = country
        try:
            payload = await self.http.get_json(
                f"{ORIGIN}?{urlencode(params)}",
                conditional=False,
                max_redirects=0,
            )
            if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
                raise ValueError("Invalid GLEIF candidates")
            rows: list[LeiCandidate] = []
            seen: set[str] = set()
            for item in payload["data"][:10]:
                attributes = item["attributes"]
                lei = lei_number(attributes["lei"])
                if lei is None or item["id"] != lei:
                    raise ValueError("Invalid GLEIF candidate identity")
                entity = attributes["entity"]
                candidate = LeiCandidate(
                    lei,
                    _text(entity["legalName"]["name"]),
                    _text(entity["jurisdiction"]),
                    _text(entity["status"]),
                )
                if country and entity["legalAddress"]["country"] != country:
                    continue
                if lei not in seen:
                    seen.add(lei)
                    rows.append(candidate)
            return tuple(rows)
        except (FeedFetchError, ValueError, KeyError, TypeError):
            raise InvalidRequest(
                "GLEIF candidates are unavailable. No candidate was selected."
            ) from None
