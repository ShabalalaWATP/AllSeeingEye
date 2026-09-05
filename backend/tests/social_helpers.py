"""Deterministic fixtures for the social board and background sampler."""

from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from ase.domain.collection import CollectionPlan, numbered
from ase.domain.events import Category, Event
from ase.domain.social import SocialBaseline, WatchedTerm
from feeds_helpers import NOW, make_event


def social_post(key: str, title: str = "#Ukraine update", *, when: datetime = NOW) -> Event:
    return make_event(
        key,
        title=title,
        summary=None,
        category=Category.SOCIAL,
        published_at=when - timedelta(minutes=30),
    ).with_changes(
        tags=frozenset({"mastodon", "ukraine"}), attributes={"instance": "mastodon.social"}
    )


def social_plan(owner: UUID, terms: list[str], *, enabled: bool = True) -> CollectionPlan:
    return CollectionPlan(
        uuid4(),
        "Private plan",
        "",
        None,
        (),
        numbered([("Question", [("Requirement", terms, [])])]),
        enabled,
        owner,
        NOW,
        NOW,
    )


class FixedTerms:
    def __init__(self, terms: tuple[WatchedTerm, ...]) -> None:
        self.terms = terms

    async def configured(self) -> tuple[WatchedTerm, ...]:
        return self.terms


class MemoryActivity:
    def __init__(self) -> None:
        self.rows: dict[datetime, Mapping[str, int]] = {}
        self.means: Mapping[str, SocialBaseline] = {}
        self.queries: list[tuple[datetime, datetime, Sequence[str]]] = []
        self.fail = False

    async def record(self, hour: datetime, counts: Mapping[str, int]) -> None:
        if self.fail:
            self.fail = False
            raise RuntimeError("Unavailable")
        self.rows[hour] = dict(counts)

    async def baselines(
        self, since: datetime, before: datetime, keys: Sequence[str]
    ) -> Mapping[str, SocialBaseline]:
        self.queries.append((since, before, keys))
        return self.means
