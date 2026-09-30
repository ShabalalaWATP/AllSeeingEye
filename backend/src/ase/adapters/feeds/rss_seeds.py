"""The seeded RSS and Atom catalogue: packaged rows turned into source specs and item options.

Rows, not code. Each group lives in ``ase/resources/feeds/rss_<group>.json`` with its
provenance note, its named licence texts and its named item options; every field is
validated here and a malformed row fails import. Grades follow docs/02_DATA_SOURCES.md
(B for wires and public broadcasters, C for national press, C with `state_controlled` for
state media, F for unassessed publisher feeds). Feeds that answered 404 or 403 to a polite
fetch (Focus Taiwan, NHK World, Kyodo) are left out until their URLs are confirmed; Kyiv
Independent's news-archive feed was verified on 13 September 2026 and ISW is read through
its posts index by a dedicated connector.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import timedelta
from types import MappingProxyType
from typing import Any, Final

from ase.adapters.feeds.rss import RssOptions
from ase.adapters.packaged_json import (
    CatalogueError,
    choice,
    fields,
    flag,
    https_url,
    integer,
    language,
    lines,
    load_resource,
    name,
    names,
    records,
    text,
    unique,
)
from ase.domain.events import Category, Credibility, Reliability
from ase.domain.source_ratings import COMMON_LIMITATIONS, SOURCE_RATING_POLICY_VERSION, SourceRating
from ase.domain.sources import SourceKind, SourceSpec

GROUPS: Final = (
    "official",
    "outlets",
    "regional",
    "native",
    "economy",
    "cyber",
    "uk_news",
    "world_news",
    "gap_news",
)
MAX_SEEDS_PER_GROUP: Final = 100
MAX_POLL_MINUTES: Final = 24 * 60
_OPTION_KEYS: Final = (
    "subtype",
    "tags",
    "credibility",
    "rationale",
    "headlines_only",
    "newest_first",
)
_SEED_KEYS: Final = (
    "id",
    "name",
    "organisation",
    "category",
    "url",
    "homepage",
    "reliability",
    "poll_minutes",
    "language",
    "options",
    "licence",
    "flags",
)
_CREDIBILITY: Final = {grade.name.lower(): grade for grade in Credibility}


@dataclass(frozen=True, slots=True)
class RssSeed:
    spec: SourceSpec
    options: RssOptions = field(default_factory=RssOptions)


def _publisher_rating(name: str, scope: str) -> SourceRating:
    """An explicit unassessed rating for a publisher headline feed with a declared scope."""
    return SourceRating(
        policy_version=SOURCE_RATING_POLICY_VERSION,
        status="unassessed",
        assessed_grade=None,
        basis=f"{name} publishes this public RSS feed; endpoint availability does not "
        "establish publisher reliability or verify its individual claims.",
        scope=scope + " Publisher coverage does not establish incident geography.",
        limitations=(
            *COMMON_LIMITATIONS,
            "One bounded feed snapshot, not a complete archive. Retained headlines only; "
            "shared ownership and syndicated reporting do not add independent corroboration.",
        ),
        provenance_role="publisher",
        publisher_reliability_assessed=False,
    )


def _options(where: str, value: object) -> RssOptions:
    row = fields(where, value, _OPTION_KEYS, ("country_category_domain", "translate_on_demand"))
    domain = row.get("country_category_domain")
    return RssOptions(
        subtype=name(f"{where}.subtype", row["subtype"]),
        tags=frozenset(names(f"{where}.tags", row["tags"], empty=True)),
        credibility=_CREDIBILITY[choice(f"{where}.credibility", row["credibility"], _CREDIBILITY)],
        rationale=text(f"{where}.rationale", row["rationale"], limit=240),
        country_category_domain=None
        if domain is None
        else text(f"{where}.country_category_domain", domain),
        headlines_only=flag(f"{where}.headlines_only", row["headlines_only"]),
        newest_first=flag(f"{where}.newest_first", row["newest_first"]),
        translate_on_demand=flag(
            f"{where}.translate_on_demand", row.get("translate_on_demand", False)
        ),
    )


def _named(where: str, value: object) -> dict[str, Any]:
    if not isinstance(value, dict) or not value:
        raise CatalogueError(f"{where}: expected a non-empty object of named entries")
    for key in value:
        name(f"{where} key", key)
    return value


def _seed(
    where: str,
    value: object,
    options: Mapping[str, RssOptions],
    licences: Mapping[str, str],
) -> RssSeed:
    row = fields(where, value, _SEED_KEYS, ("rating_scope", "note"))
    source_id = name(f"{where}.id", row["id"])
    if "note" in row:
        text(f"{where}.note", row["note"])
    title = text(f"{where}.name", row["name"], limit=120)
    rating = None
    if "rating_scope" in row:
        rating = _publisher_rating(title, text(f"{where}.rating_scope", row["rating_scope"]))
    categories = {category.value for category in Category}
    reliability = {grade.value for grade in Reliability}
    minutes = integer(f"{where}.poll_minutes", row["poll_minutes"], 1, MAX_POLL_MINUTES)
    spec = SourceSpec(
        id=source_id,
        name=title,
        organisation=text(f"{where}.organisation", row["organisation"], limit=160),
        category=Category(choice(f"{where}.category", row["category"], categories)),
        kind=SourceKind.RSS,
        url=https_url(f"{where}.url", row["url"]),
        reliability=Reliability(choice(f"{where}.reliability", row["reliability"], reliability)),
        poll_interval=timedelta(minutes=minutes),
        language=language(f"{where}.language", row["language"]),
        licence_note=licences[choice(f"{where}.licence", row["licence"], licences)],
        homepage=https_url(f"{where}.homepage", row["homepage"]),
        flags=frozenset(names(f"{where}.flags", row["flags"], empty=True)),
        rating=rating,
    )
    return RssSeed(spec, options[choice(f"{where}.options", row["options"], options)])


def _load(group: str) -> tuple[tuple[RssSeed, ...], Mapping[str, RssOptions]]:
    where = f"feeds/rss_{group}.json"
    raw = load_resource("feeds", f"rss_{group}.json")
    data = fields(where, raw, ("about", "licences", "options", "seeds"))
    lines(f"{where}.about", data["about"])
    licences = {
        key: text(f"{where}.licences.{key}", value, limit=600)
        for key, value in _named(f"{where}.licences", data["licences"]).items()
    }
    options = {
        key: _options(f"{where}.options.{key}", value)
        for key, value in _named(f"{where}.options", data["options"]).items()
    }
    rows = records(f"{where}.seeds", data["seeds"], MAX_SEEDS_PER_GROUP)
    seeds = tuple(
        _seed(f"{where}.seeds[{index}]", row, options, licences) for index, row in enumerate(rows)
    )
    used_options = {row["options"] for row in rows}
    used_licences = {row["licence"] for row in rows}
    if used_options != set(options) or used_licences != set(licences):
        raise CatalogueError(f"{where}: a named option or licence is not used by any seed")
    return seeds, MappingProxyType(options)


def _catalogue() -> dict[str, tuple[tuple[RssSeed, ...], Mapping[str, RssOptions]]]:
    loaded = {group: _load(group) for group in GROUPS}
    seeds = [seed for group_seeds, _ in loaded.values() for seed in group_seeds]
    unique("RSS catalogue ids", [seed.spec.id for seed in seeds])
    unique("RSS catalogue URLs", [seed.spec.url for seed in seeds])
    return loaded


_LOADED: Final = _catalogue()
OFFICIAL_SEEDS: Final[tuple[RssSeed, ...]] = _LOADED["official"][0]
OUTLET_SEEDS: Final[tuple[RssSeed, ...]] = _LOADED["outlets"][0]
NATIVE_SEEDS: Final[tuple[RssSeed, ...]] = _LOADED["native"][0]
REGIONAL_SEEDS: Final[tuple[RssSeed, ...]] = _LOADED["regional"][0] + NATIVE_SEEDS
ECONOMY_SEEDS: Final[tuple[RssSeed, ...]] = _LOADED["economy"][0]
CYBER_SEEDS: Final[tuple[RssSeed, ...]] = _LOADED["cyber"][0]
UK_NEWS_SEEDS: Final[tuple[RssSeed, ...]] = _LOADED["uk_news"][0]
WORLD_NEWS_SEEDS: Final[tuple[RssSeed, ...]] = _LOADED["world_news"][0]
GAP_NEWS_SEEDS: Final[tuple[RssSeed, ...]] = _LOADED["gap_news"][0]
# Additional live headline sources, separate from the bounded private provider inventory.
NEWS_SEEDS: Final[tuple[RssSeed, ...]] = UK_NEWS_SEEDS + WORLD_NEWS_SEEDS + GAP_NEWS_SEEDS
OPTION_PRESETS: Final[Mapping[str, Mapping[str, RssOptions]]] = MappingProxyType(
    {group: presets for group, (_, presets) in _LOADED.items()}
)
US_ADVISORY: Final = OPTION_PRESETS["official"]["us_travel_advisory"]
