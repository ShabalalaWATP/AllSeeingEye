"""Retention budgets: the live store is a cache with hard limits, never an archive."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import timedelta

from ase.domain.events import Category


@dataclass(frozen=True, slots=True)
class RetentionBudget:
    window: timedelta
    max_items: int


DEFAULT_BUDGETS: Mapping[Category, RetentionBudget] = {
    Category.AVIATION: RetentionBudget(timedelta(minutes=10), 15_000),
    Category.MARITIME: RetentionBudget(timedelta(minutes=30), 20_000),
    Category.DISASTER: RetentionBudget(timedelta(days=7), 150_000),
    Category.NEWS: RetentionBudget(timedelta(hours=72), 40_000),
    Category.CONFLICT: RetentionBudget(timedelta(days=30), 30_000),
    Category.SOCIAL: RetentionBudget(timedelta(hours=24), 10_000),
    Category.SPACE: RetentionBudget(timedelta(days=7), 5_000),
    Category.CYBER: RetentionBudget(timedelta(days=7), 5_000),
    Category.POLITICAL: RetentionBudget(timedelta(days=7), 5_000),
    Category.HUMANITARIAN: RetentionBudget(timedelta(days=7), 5_000),
    Category.ECONOMIC: RetentionBudget(timedelta(days=7), 5_000),
}

DEFAULT_MEMORY_BUDGET_BYTES = 512 * 1024 * 1024
FALLBACK_BUDGET = RetentionBudget(timedelta(days=1), 5_000)


def budget_for(
    category: Category, overrides: Mapping[Category, RetentionBudget] | None = None
) -> RetentionBudget:
    if overrides and category in overrides:
        return overrides[category]
    return DEFAULT_BUDGETS.get(category, FALLBACK_BUDGET)
