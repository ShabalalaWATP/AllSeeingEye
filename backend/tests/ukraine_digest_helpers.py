"""Fixtures for the fortnightly Ukraine digest: a board, a pack and a scripted model."""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime, timedelta
from types import MappingProxyType
from typing import Any
from unittest.mock import AsyncMock

from ase.application.ukraine import Freshness, UkraineBoard, UpdateEntry
from ase.application.ukraine_digest import UkraineDigestService
from ase.application.ukraine_digest_writer import DigestWriter
from ase.domain.events import Category
from ase.domain.llm import LlmResult
from ase.domain.ukraine.digest import StoredDigest
from ase.domain.ukraine.lenses import Lens
from ase.domain.ukraine.losses import ClaimedLosses
from ase.domain.ukraine.updates import update_group
from feeds_helpers import make_event
from helpers import FakeClock

NOW = datetime(2026, 9, 1, 12, tzinfo=UTC)
PERIOD_END = NOW.date()
PERIOD_START = PERIOD_END - timedelta(days=14)

# Source, title, summary, category, lenses and how many days before "now" it was published.
ITEMS: tuple[tuple[str, str, str, str, Category, frozenset[Lens], int], ...] = (
    (
        "isw-a",
        "isw_assessments",
        "Russian offensive campaign assessment",
        "Russian forces continued attacks near the eastern city, with marginal advances.",
        Category.CONFLICT,
        frozenset(),
        1,
    ),
    (
        "isw-b",
        "isw_assessments",
        "Russian offensive campaign assessment, later",
        "Ukrainian forces reported counterattacks in the same sector.",
        Category.CONFLICT,
        frozenset(),
        3,
    ),
    (
        "ki-a",
        "kyiv_independent",
        "Strikes reported on energy infrastructure",
        "Regional authorities reported damage to substations overnight.",
        Category.CONFLICT,
        frozenset({Lens.STRIKES}),
        1,
    ),
    (
        "ki-b",
        "kyiv_independent",
        "Fighting reported near a front line town",
        "Both sides reported continued fighting without confirmed change of control.",
        Category.CONFLICT,
        frozenset(),
        4,
    ),
    (
        "ur-a",
        "ukrinform_en",
        "Air defence reported intercepts overnight",
        "The air force reported intercepts of attack drones.",
        Category.CONFLICT,
        frozenset({Lens.EQUIPMENT}),
        5,
    ),
    (
        "pol-a",
        "kyiv_independent",
        "European ministers discussed further support",
        "Ministers met to discuss funding, with no final decision reported.",
        Category.POLITICAL,
        frozenset({Lens.DIPLOMACY}),
        2,
    ),
    (
        "pol-b",
        "meduza_en",
        "Russian officials commented on talks",
        "Officials repeated existing positions, according to state reporting.",
        Category.POLITICAL,
        frozenset(),
        6,
    ),
)


def updates(now: datetime) -> tuple[UpdateEntry, ...]:
    entries = []
    for key, source_id, title, summary, category, lenses, days_ago in ITEMS:
        at = now - timedelta(days=days_ago)
        event = make_event(
            key,
            source_id=source_id,
            category=category,
            title=title,
            summary=summary,
            published_at=at,
            observed_at=at,
            country_iso="UA",
        )
        entries.append(UpdateEntry(event, update_group(source_id), lenses))
    return tuple(entries)


def claim(now: datetime) -> ClaimedLosses:
    return ClaimedLosses(
        reported_on=now.date() - timedelta(days=1),
        day=1286,
        source_url="https://example.invalid/claim",
        totals=MappingProxyType({"personnel_units": 1_000_000, "tanks": 11_000}),
        increase=MappingProxyType({"personnel_units": 900, "tanks": 4}),
    )


CLAIM = claim(NOW)


def board(now: datetime = NOW, **changes: object) -> UkraineBoard:
    values: dict[str, Any] = {
        "generated_at": now,
        "day_number": 1286,
        "day_basis": "claimed",
        "window_days": 14,
        "events_scanned": len(ITEMS),
        "updates": updates(now),
        "lens_counts": {},
        "claims": (claim(now),),
        "control": None,
        "confirmed": None,
        "civilian_harm": None,
        "lens_series": (),
        "freshness": Freshness(None, None, None, None),
    }
    values.update(changes)
    return UkraineBoard(**values)


def answer(
    *,
    starts_on: date = PERIOD_START,
    ends_on: date = PERIOD_END,
    battlefield_text: str = (
        "Reporting suggests fighting continued in the east without confirmed change of control."
    ),
    political_text: str = (
        "European ministers met to discuss further funding, with no final decision reported."
    ),
    ids: tuple[str, ...] = ("e1",),
) -> str:
    """A well formed answer; the defaults pass every mechanical check."""
    return json.dumps(
        {
            "period": {"from": starts_on.isoformat(), "to": ends_on.isoformat()},
            "battlefield": {
                "summary": (
                    "Reporting suggests the fortnight brought little confirmed change on the "
                    "ground, with continued strikes and continued fighting in the east."
                ),
                "changes": [
                    {"text": battlefield_text, "source_ids": list(ids)},
                    {
                        "text": (
                            "Regional authorities reported damage to energy substations "
                            "overnight, according to Ukrainian reporting."
                        ),
                        "source_ids": ["e3"],
                    },
                ],
            },
            "political": {
                "summary": (
                    "Political reporting centred on further support for Ukraine, with "
                    "positions restated rather than settled."
                ),
                "changes": [
                    {"text": political_text, "source_ids": ["e6"]},
                    {
                        "text": (
                            "Russian officials repeated existing positions on talks, "
                            "according to reporting collected here."
                        ),
                        "source_ids": ["e7"],
                    },
                ],
            },
            "watch": [
                "Whether reported strikes on energy infrastructure continue into winter.",
                "Whether the discussed funding turns into a stated decision.",
            ],
            "caveats": ["This digest reads only the sources listed and cannot verify any of them."],
        }
    )


def result(content: str) -> LlmResult:
    return LlmResult(content, "fixture-model", 120.0, 900, 300)


def scripted_gateway(*, ids: tuple[str, ...] = ("e1",)) -> AsyncMock:
    """Answers whatever period the pack asked about, so the clock can move in tests."""
    gateway = AsyncMock()

    async def respond(_base_url: str, _key: str, _model: str, request: Any) -> LlmResult:
        period = json.loads(request.messages[1].content)["period"]
        return result(
            answer(
                starts_on=date.fromisoformat(period["from"]),
                ends_on=date.fromisoformat(period["to"]),
                ids=ids,
            )
        )

    gateway.complete.side_effect = respond
    return gateway


class FakeDigestStore:
    def __init__(self) -> None:
        self.saved: list[StoredDigest] = []

    async def recent(self, limit: int) -> list[StoredDigest]:
        return list(self.saved[:limit])

    async def save(self, digest: StoredDigest, keep: int) -> None:
        self.saved.insert(0, digest)
        del self.saved[keep:]


class FakeAdmission:
    def __init__(self) -> None:
        self.entered = 0

    @asynccontextmanager
    async def guard(self) -> Iterator[None]:  # type: ignore[misc]
        self.entered += 1
        yield


class FakeRuntime:
    def __init__(self, profile: object | None) -> None:
        self.value = profile

    async def profile(self) -> object | None:
        return self.value


def service(
    *,
    store: FakeDigestStore,
    runtime: FakeRuntime,
    writer: DigestWriter,
    clock: FakeClock,
    limiter: object,
    admission: FakeAdmission,
    audit: list[tuple[object, str | None]],
    board_value: UkraineBoard | None = None,
) -> UkraineDigestService:
    async def record(actor_id: Any, ip: str | None) -> None:
        audit.append((actor_id, ip))

    return UkraineDigestService(
        lambda: board_value if board_value is not None else board(clock.now()),
        store,  # type: ignore[arg-type]
        runtime,  # type: ignore[arg-type]
        writer,
        clock,
        admission,  # type: ignore[arg-type]
        limiter,  # type: ignore[arg-type]
        record,
    )
