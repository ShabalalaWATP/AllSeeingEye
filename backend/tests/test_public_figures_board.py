"""Public figures board cost: identical matches, bounded searches, off-loop and admitted reads."""

from __future__ import annotations

import asyncio
import re
import threading
from collections.abc import Callable
from datetime import timedelta
from typing import Any, cast

import pytest
from httpx import AsyncClient

from ase.adapters.geo.public_figures import load_public_figures
from ase.adapters.store.memory import InMemoryEventStore
from ase.application import public_figures as service_module
from ase.application.public_figures import FigureBoard, PublicFigureService
from ase.container import Container
from ase.domain.errors import RateLimited
from ase.domain.events import Category
from ase.domain.public_figures import (
    MAX_FIGURES,
    MAX_MENTION_TEXT,
    NameMatcher,
    PublicFigure,
    _person_patterns,
    match_people,
    name_matcher,
)
from ase.domain.users import User
from feeds_helpers import NOW, FakeClock, make_event
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token

FILLER = "officials said talks continued overnight while envoys met near the border " * 6


def figure(key: str, name: str, aliases: tuple[str, ...] = ()) -> PublicFigure:
    return PublicFigure(
        id=key,
        wikidata_id=f"Q{key}",
        name=name,
        office="Office",
        role="head_of_state",
        country_iso="GB",
        organisation=None,
        aliases=aliases,
        seat_name="London",
        seat_lat=51.5,
        seat_lon=-0.12,
        portrait=None,
    )


def every_pattern(
    text: str, patterns: tuple[tuple[str, str, re.Pattern[str]], ...]
) -> dict[str, str]:
    """The previous matcher: every word-bounded pattern searched, longest name first."""
    folded = " ".join(text[:MAX_MENTION_TEXT].casefold().split())
    found: dict[str, str] = {}
    for person_id, name, pattern in patterns:
        if person_id not in found and pattern.search(folded):
            found[person_id] = name
    return found


def roster() -> tuple[PublicFigure, ...]:
    extra = (
        figure("k", "Kim Jong-un", ("Kim Jong Un",)),
        figure("l", "Luiz Inácio Lula da Silva"),
        figure("q", "'Abdullah Bin"),  # starts with a non-word character
    )
    return load_public_figures().figures[: MAX_FIGURES - len(extra)] + extra


def texts(figures: tuple[PublicFigure, ...]) -> list[str]:
    names = [name for _, name, _ in _person_patterns(figures)]
    shapes = (
        "{n}",
        "said {n}.",
        "({n})",
        "x{n} and {n}x",
        "{n}'s visit",
        "pre-{n}-post",
        "  {N}  arrived  ",
        "{n}_",
        "{n}ab officials said talks continued",
    )
    cases = [shape.format(n=name, N=name.upper()) for name in names for shape in shapes]
    cases += [
        f"talks: {a} met {b} and {c}" for a, b, c in zip(names, names[3:], names[7:], strict=False)
    ]
    cases += [FILLER, "", "Luiz Inácio Lula da Silva", "KIM JONG UN, kim jong-un"]
    return cases


def test_indexed_matching_equals_searching_every_pattern() -> None:
    figures = roster()
    assert name_matcher(figures[:MAX_FIGURES]).unindexed, "the fallback path is exercised"
    patterns = _person_patterns(figures[:MAX_FIGURES])
    cases = texts(figures)
    assert len(cases) > 3_000
    for text in cases:
        assert match_people(text, figures) == every_pattern(text, patterns), text
    assert match_people("Met 'Abdullah Bin today", figures) == {"Qq": "'abdullah bin"}
    assert match_people("x'Abdullah Bin", figures) == {}


class CountingPattern:
    def __init__(self, pattern: re.Pattern[str]) -> None:
        self.pattern = pattern
        self.calls = 0

    def search(self, text: str) -> re.Match[str] | None:
        self.calls += 1
        return self.pattern.search(text)


def test_matching_searches_only_names_whose_first_word_is_present() -> None:
    real = name_matcher(load_public_figures().figures)
    counters = [CountingPattern(pattern) for _, _, pattern in real.patterns]
    matcher = NameMatcher(
        patterns=cast(
            Any,
            tuple(
                (pid, name, c) for (pid, name, _), c in zip(real.patterns, counters, strict=True)
            ),
        ),
        by_first_word=real.by_first_word,
        unindexed=real.unindexed,
    )
    assert len(real.patterns) > 300

    assert matcher.match(FILLER + FILLER) == {}
    assert sum(c.calls for c in counters) == len(real.unindexed)

    found = matcher.match("Zelenskyy visits troops. " + FILLER)
    assert list(found.values()) == ["zelenskyy"]
    assert sum(c.calls for c in counters) == len(real.unindexed) + 1


def news(count: int) -> InMemoryEventStore:
    store = InMemoryEventStore()
    store.upsert(
        [
            make_event(
                f"n{i}",
                category=Category.NEWS,
                subtype="news_report",
                title="Zelenskyy visits front-line troops" if i % 2 else "Markets steady",
                summary=FILLER,
                published_at=NOW - timedelta(minutes=i),
                point=None,
            )
            for i in range(count)
        ]
    )
    return store


async def test_board_matches_off_the_event_loop_with_the_same_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = news(40)
    catalogue = load_public_figures()
    threads: list[int] = []

    def recording(figures: tuple[PublicFigure, ...]) -> NameMatcher:
        threads.append(threading.get_ident())
        return name_matcher(figures)

    monkeypatch.setattr(service_module, "name_matcher", recording)
    board = await PublicFigureService(store, FakeClock(NOW), catalogue).board(admission_key="u")
    assert threads and threading.get_ident() not in threads

    class PlainStore:
        """A port fake without the cooperative reader still gets the same board."""

        def query(self, query: Any) -> list[Any]:
            return store.query(query)

    plain = PublicFigureService(cast(Any, PlainStore()), FakeClock(NOW), catalogue)
    assert summary(await plain.board(admission_key="u")) == summary(board)
    assert next(c.mentions for c in board.cards if c.figure.id == "ua-head-of-state") == 20


def summary(board: FigureBoard) -> dict[str, int]:
    return {card.figure.wikidata_id: card.mentions for card in board.cards}


async def test_board_admits_two_reads_per_caller_and_refuses_a_third(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate = threading.Event()

    def held(figures: tuple[PublicFigure, ...]) -> NameMatcher:
        gate.wait(5)
        return name_matcher(figures)

    monkeypatch.setattr(service_module, "name_matcher", held)
    service = PublicFigureService(news(10), FakeClock(NOW), load_public_figures())
    running = [asyncio.create_task(service.board(admission_key="user:a")) for _ in range(2)]
    try:
        for _ in range(5):
            await asyncio.sleep(0)
        with pytest.raises(RateLimited):
            await service.board(admission_key="user:a")
        other = asyncio.create_task(service.board(admission_key="user:b"))
    finally:
        gate.set()
    boards = await asyncio.gather(*running, other)
    assert len({tuple(summary(board).items()) for board in boards}) == 1


async def test_route_reads_the_board_under_the_callers_admission_key(
    client: AsyncClient,
    container: Container,
    user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    keys: list[str] = []
    read = container.store.read_cooperatively

    async def spy(query: Any, project: Callable[..., Any], *, admission_key: str) -> Any:
        keys.append(admission_key)
        return await read(query, project, admission_key=admission_key)

    monkeypatch.setattr(container.store, "read_cooperatively", spy)
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    response = await client.get("/api/figures", headers=bearer(token))
    assert response.status_code == 200
    assert keys == [f"user:{user.id}"]
