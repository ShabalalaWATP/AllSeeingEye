"""UN HRMMU monthly civilian harm pages and curated casualty references, text only, bounded.

The listing page names each monthly "Protection of Civilians in Armed Conflict" page; each
page states the month's verified killed and injured in one fixed sentence. Where the sentence
is absent the month keeps its link and no figures. Operator-run, never at runtime.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, date, datetime
from html.parser import HTMLParser
from importlib.resources import files
from pathlib import Path
from typing import Any

import httpx

from ase.adapters.geo.bounded_download import DEFAULT_CONTACT, user_agent
from ase.domain.ukraine.confirmed import MAX_HARM_MONTHS, MAX_REFERENCES

SITE = "https://ukraine.ohchr.org"
LISTING = f"{SITE}/en/reports/protection-of-civilians"
REFERENCES_SEED = "ukraine_casualty_references_seeds.json"
MAX_PAGE_BYTES = 2_000_000
ATTRIBUTION = "UN Human Rights Monitoring Mission in Ukraine (HRMMU), OHCHR"
MONTHS = {
    name: index
    for index, name in enumerate(
        (
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ),
        start=1,
    )
}
_LINK = re.compile(r'href="(/en/Protection-of-Civilians-in-Armed-Conflict-([A-Z][a-z]+)-(\d{4}))"')
_SENTENCE = re.compile(
    r"At least ([\d,]+) civilians? were killed and ([\d,]+) injured in Ukraine in "
    r"([A-Z][a-z]+ \d{4})"
)
_PUBLISHED = re.compile(r'datetime="(\d{4}-\d{2}-\d{2})')
_TITLE = re.compile(r"<title>(.*?)\s*\|", re.S)


class _VisibleText(HTMLParser):
    """Extract visible text; decoded entities mean the output must be treated as text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"} and self.hidden is None:
            self.hidden = tag

    def handle_endtag(self, tag: str) -> None:
        if tag == self.hidden:
            self.hidden = None

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        # HTML ignores the self-closing slash on raw-text elements. Keep hiding
        # their contents until an explicit end tag, including malformed input.
        self.handle_starttag(tag, attrs)
        if tag in {"script", "style"}:
            self.set_cdata_mode(tag)

    def handle_data(self, data: str) -> None:
        if self.hidden is None:
            self.parts.append(data)


def _plain(markup: str) -> str:
    parser = _VisibleText()
    parser.feed(markup)
    parser.close()
    return " ".join(" ".join(parser.parts).split())


def parse_listing(markup: str) -> list[tuple[str, date]]:
    """Monthly page paths with their month, newest first, without duplicates."""
    seen: dict[str, date] = {}
    for path, month_name, year in _LINK.findall(markup):
        month = MONTHS.get(month_name)
        if month and path not in seen:
            seen[path] = date(int(year), month, 1)
    ordered = sorted(seen.items(), key=lambda item: item[1], reverse=True)
    return ordered[:MAX_HARM_MONTHS]


def parse_month(markup: str, month: date, url: str) -> dict[str, Any]:
    text = _plain(markup)
    match = _SENTENCE.search(text)
    published = _PUBLISHED.search(markup)
    title = _TITLE.search(markup)
    killed = injured = None
    if match and match.group(3) == month.strftime("%B %Y"):
        killed = int(match.group(1).replace(",", ""))
        injured = int(match.group(2).replace(",", ""))
    return {
        "month": month.isoformat(),
        "title": _plain(title.group(1))[:160] if title else month.strftime("%B %Y"),
        "url": url,
        "published_on": published.group(1) if published else None,
        "killed": killed,
        "injured": injured,
    }


def _references() -> list[dict[str, Any]]:
    data: dict[str, Any] = json.loads(files("ase.resources").joinpath(REFERENCES_SEED).read_text())
    items: list[dict[str, Any]] = data["items"]
    if len(items) > MAX_REFERENCES:
        raise ValueError("Casualty references exceed the bound")
    return items


def _page(client: httpx.Client, url: str) -> str:
    response = client.get(url, follow_redirects=True)
    response.raise_for_status()
    if len(response.content) > MAX_PAGE_BYTES:
        raise ValueError("HRMMU page exceeds the byte bound")
    return response.text


def build_snapshot(client: httpx.Client, retrieved_at: datetime) -> dict[str, Any]:
    months = [
        parse_month(_page(client, SITE + path), month, SITE + path)
        for path, month in parse_listing(_page(client, LISTING))
    ]
    return {
        "retrieved_at": retrieved_at.isoformat(timespec="seconds"),
        "source_url": LISTING,
        "attribution": ATTRIBUTION,
        "months": months,
        "references": _references(),
    }


def import_ukraine_casualties(destination: str, contact: str = DEFAULT_CONTACT) -> int:
    with httpx.Client(timeout=60, headers={"User-Agent": user_agent(contact)}) as client:
        snapshot = build_snapshot(client, datetime.now(UTC))
    Path(destination).write_text(json.dumps(snapshot, separators=(",", ":")), encoding="utf-8")
    return len(snapshot["months"])
