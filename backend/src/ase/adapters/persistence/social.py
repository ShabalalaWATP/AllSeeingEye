"""Bounded social activity storage and configuration readers with private sessions."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.baselines import SqlBaselineRepository
from ase.adapters.persistence.direction import SqlPlanRepository
from ase.adapters.persistence.models import ActivitySampleRow
from ase.domain.social import MAX_TERMS, SocialBaseline, WatchedTerm, vocabulary

KIND_SOCIAL = "social_keyword"
BASELINE_DAYS = 30


class SqlSocialTerms:
    def __init__(self, session_factory: Callable[[], AsyncSession], watch: Sequence[str]) -> None:
        self._sessions = session_factory
        self._watch = tuple(watch)

    async def configured(self) -> tuple[WatchedTerm, ...]:
        async with self._sessions() as session:
            return vocabulary(self._watch, await SqlPlanRepository(session).list_all())


class SqlSocialActivity:
    """At most 32 keyword digests per hour over 30 days. No raw post text is written."""

    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._sessions = session_factory

    async def record(self, hour: datetime, counts: Mapping[str, int]) -> None:
        if len(counts) > MAX_TERMS or any(
            not re.fullmatch(r"[0-9a-f]{32}", key)
            or isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
            for key, value in counts.items()
        ):
            raise ValueError("Invalid social activity sample")
        hour = hour.replace(minute=0, second=0, microsecond=0)
        cutoff = hour + timedelta(hours=1) - timedelta(days=BASELINE_DAYS)
        async with self._sessions() as session:
            await session.execute(
                delete(ActivitySampleRow).where(
                    ActivitySampleRow.kind == KIND_SOCIAL,
                    (ActivitySampleRow.hour < cutoff) | ActivitySampleRow.key.not_in(list(counts)),
                )
            )
            repository = SqlBaselineRepository(session)
            for key, value in counts.items():
                await repository.record(KIND_SOCIAL, key, hour, value)
            await session.commit()

    async def baselines(
        self, since: datetime, before: datetime, keys: Sequence[str]
    ) -> Mapping[str, SocialBaseline]:
        if not keys:
            return {}
        async with self._sessions() as session:
            result = await session.execute(
                select(ActivitySampleRow.key, func.avg(ActivitySampleRow.value), func.count())
                .where(
                    ActivitySampleRow.kind == KIND_SOCIAL,
                    ActivitySampleRow.hour >= since,
                    ActivitySampleRow.hour < before,
                    ActivitySampleRow.key.in_(keys[:MAX_TERMS]),
                )
                .group_by(ActivitySampleRow.key)
            )
            return {
                str(key): SocialBaseline(float(mean), int(hours))
                for key, mean, hours in result.all()
            }
