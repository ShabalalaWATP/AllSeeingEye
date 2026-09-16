"""Synthetic economy figures, headlines and a valid explainer payload for the checks."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock

from ase.application.economy_news import EconomyNews, EconomyNewsItem
from ase.domain.economy import EconomyPoint, EconomyRegion, EconomySeries, EconomySnapshot
from ase.domain.economy_explainer import REGION_IDS
from llm_fixture_helpers import seed_legacy_profile

NOW = datetime(2026, 9, 1, 12, tzinfo=UTC)
REGION_NAMES = (
    ("WORLD", "Worldwide"),
    ("GB", "United Kingdom"),
    ("US", "United States"),
    ("RU", "Russia"),
    ("CN", "China"),
    ("IR", "Iran"),
)


def annual(
    key: str,
    name: str,
    unit: str,
    points: list[tuple[str, float | None]],
    *,
    status: str = "available",
) -> EconomySeries:
    return EconomySeries(
        key,
        name,
        unit,
        "annual",
        "World Bank",
        "https://data.worldbank.org/indicator/NY.GDP.MKTP.KD.ZG",
        status,  # type: ignore[arg-type]
        "Annual published observations, not forecasts.",
        NOW,
        tuple(EconomyPoint(date, value) for date, value in points),
    )


def region_series(growth: float = 2.4) -> tuple[EconomySeries, ...]:
    return (
        annual("growth", "GDP growth", "% annual change", [("2023", 1.2), ("2024", growth)]),
        annual(
            "inflation",
            "Consumer price inflation",
            "% annual change",
            [("2022", 5.0), ("2023", None), ("2024", 3.0)],
        ),
        annual("unemployment", "Unemployment", "% of labour force", [], status="unavailable"),
    )


def fx_series() -> tuple[EconomySeries, ...]:
    return (
        EconomySeries(
            "GBP",
            "GBP per euro",
            "GBP per EUR",
            "daily",
            "European Central Bank",
            "https://www.ecb.europa.eu/stats",
            "available",
            "Currency units per 1 euro, published on working days.",
            NOW,
            (EconomyPoint("2026-08-31", 0.85), EconomyPoint("2026-09-01", 0.86)),
        ),
    )


def snapshot(growth: float = 2.4, fetched_at: datetime = NOW) -> EconomySnapshot:
    return EconomySnapshot(
        fetched_at,
        fetched_at,
        tuple(EconomyRegion(code, name, region_series(growth)) for code, name in REGION_NAMES),
        fx_series(),
    )


def headline(index: int = 1) -> EconomyNewsItem:
    return EconomyNewsItem(
        f"news-{index}",
        f"Shop prices rise more slowly than last year, report number {'I' * index}",
        "https://publisher.example.invalid/story",
        "reuters_business",
        "Reuters Business",
        "Reuters",
        datetime(2026, 8, 31, 9, tzinfo=UTC),
        ("GB",),
        "publisher",
    )


def news(count: int = 1) -> EconomyNews:
    return EconomyNews(
        tuple(headline(index) for index in range(1, count + 1)),
        NOW,
        48,
        "Bounded publisher headlines.",
    )


SECTION = {
    "takeaway": "Growth picked up a little in 2024 while price rises slowed.",
    "paragraphs": [
        "The economy grew by 2.4% in 2024, up from 1.2% in 2023. That is faster, "
        "but it is still a modest pace, so most people will not feel a sudden change.",
        "Price rises slowed to 3% in 2024 from 5% in 2022. One likely reason is that "
        "energy costs settled down, although the figures alone cannot show that.",
    ],
    "drivers": [
        "Prices were rising at 3% in 2024, slower than in 2022.",
        "Growth of 2.4% in 2024 was better than the 1.2% recorded in 2023.",
    ],
    "watch": [
        "Whether price rises keep slowing next year.",
        "Whether growth holds up once older figures are revised.",
    ],
}
REGION_SECTION = {
    "takeaway": "The picture is steady, with faster growth and slower price rises.",
    "paragraphs": [
        "Growth reached 2.4% in 2024 after 1.2% in 2023, and shop prices rose by 3% "
        "in 2024. The latest unemployment figure is not published here, so that part "
        "of the picture is missing."
    ],
    "drivers": ["Growth of 2.4% in 2024 was the strongest figure supplied."],
    "watch": ["Whether the missing unemployment figure is published later."],
}
GLOSSARY = [
    {"term": "Inflation", "plain_english": "How quickly prices in the shops go up over a year."},
    {
        "term": "GDP growth",
        "plain_english": "How much more, or less, a country produced than last year.",
    },
    {
        "term": "Reference rate",
        "plain_english": (
            "A daily published exchange rate for information, not a price to trade at."
        ),
    },
]


def payload() -> dict[str, object]:
    return {
        "world": dict(SECTION),
        "regions": {key: dict(REGION_SECTION) for key in REGION_IDS[1:]},
        "glossary": [dict(entry) for entry in GLOSSARY],
    }


def content(**overrides: object) -> str:
    body = payload()
    body.update(overrides)
    return json.dumps(body)


async def explainer_profile(container):
    return await seed_legacy_profile(
        container,
        {
            "name": "Economy explainer fixture",
            "base_url": "https://model.example.invalid/v1",
            "model": "gpt-5.6-luna",
            "api_key": "synthetic-economy-key",
            "roles": ["assessment", "direction", "devil", "translation"],
            "max_output_tokens": 8000,
            "temperature": 0.2,
        },
    )


def install(container, monkeypatch, *, growth: float = 2.4, headlines: int = 1) -> None:
    """Serve fixed figures and headlines instead of any public provider."""
    monkeypatch.setattr(container.economy, "snapshot", AsyncMock(return_value=snapshot(growth)))
    monkeypatch.setattr(container.economy_news, "read", AsyncMock(return_value=news(headlines)))
