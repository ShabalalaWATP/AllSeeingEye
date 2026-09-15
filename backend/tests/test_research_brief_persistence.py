"""Immutable, scoped Research Brief revisions on disposable SQLite."""

import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from ase.adapters.persistence import models as _models  # noqa: F401
from ase.adapters.persistence import teams as _teams  # noqa: F401
from ase.adapters.persistence.base import Base
from ase.adapters.persistence.research_brief_models import ResearchBriefRevisionRow
from ase.adapters.persistence.research_briefs import SqlResearchBriefRepository
from ase.domain.errors import Conflict, Forbidden
from ase.domain.research import ResearchMode
from ase.domain.research_brief import ResearchBrief
from ase.domain.research_brief_scope import BriefCollection, BriefObservation, BriefScope
from ase.domain.research_brief_values import (
    BriefIdentity,
    BriefLens,
    BriefLimits,
    BriefMonitoring,
    BriefOutput,
    BriefQuestion,
)

NOW = datetime(2026, 9, 14, 12, tzinfo=UTC)


def _brief(*, owner_id=None, team_id=None) -> ResearchBrief:
    owner_id = owner_id or uuid4()
    return ResearchBrief(
        identity=BriefIdentity(
            id=uuid4(),
            revision=1,
            owner_id=owner_id,
            team_id=team_id,
            title="Regional developments",
            created_at=NOW,
            revised_at=NOW,
        ),
        question=BriefQuestion(main="What changed in the region?"),
        scope=BriefScope(),
        observation=BriefObservation(policy="template_default"),
        lens=BriefLens(),
        collection=BriefCollection(),
        output=BriefOutput(depth=ResearchMode.QUICK),
        limits=BriefLimits(),
        monitoring=BriefMonitoring(),
    )


@pytest.mark.asyncio
async def test_revisions_are_insert_only_and_scoped() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        maker = async_sessionmaker(engine, expire_on_commit=False)
        owner, team, stranger = uuid4(), uuid4(), uuid4()
        brief = _brief(owner_id=owner, team_id=team)
        async with maker() as session:
            repo = SqlResearchBriefRepository(session)
            with pytest.raises(Forbidden):
                await repo.add_revision(brief, actor_id=stranger)
            await repo.add_revision(brief, actor_id=owner, authorised_team_ids=(team,))
            await session.commit()
        async with maker() as session:
            repo = SqlResearchBriefRepository(session)
            assert await repo.get_revision(brief.identity.id, 1, actor_id=owner) == brief
            assert await repo.get_revision(brief.identity.id, 1, actor_id=stranger) is None
            assert (
                await repo.get_revision(
                    brief.identity.id, 1, actor_id=stranger, authorised_team_ids=(team,)
                )
                == brief
            )
            changed = brief.revise(
                at=NOW + timedelta(minutes=1),
                question=BriefQuestion(main="What changed since yesterday?"),
            )
            await repo.add_revision(changed, actor_id=owner, authorised_team_ids=(team,))
            await repo.add_revision(changed, actor_id=owner, authorised_team_ids=(team,))
            with pytest.raises(Conflict):
                await repo.add_revision(
                    brief.revise(
                        at=NOW + timedelta(minutes=2),
                        question=BriefQuestion(main="A different same-number revision"),
                    ),
                    actor_id=owner,
                    authorised_team_ids=(team,),
                )
            await session.commit()
        async with maker() as session:
            repo = SqlResearchBriefRepository(session)
            assert await repo.get_revision(brief.identity.id, 1, actor_id=owner) == brief
            assert await repo.latest_revision(brief.identity.id, actor_id=owner) == changed
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_stored_digest_and_schema_are_verified_before_use() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        maker = async_sessionmaker(engine, expire_on_commit=False)
        owner = uuid4()
        brief = _brief(owner_id=owner)
        key = (brief.identity.id, 1)
        async with maker() as session:
            repo = SqlResearchBriefRepository(session)
            await repo.add_revision(brief, actor_id=owner)
            await session.commit()
        async with maker() as session:
            await session.execute(
                update(ResearchBriefRevisionRow)
                .where(
                    ResearchBriefRevisionRow.brief_id == key[0],
                    ResearchBriefRevisionRow.revision == key[1],
                )
                .values(payload_sha256="0" * 64)
            )
            await session.commit()
        async with maker() as session:
            with pytest.raises(Conflict, match="integrity"):
                await SqlResearchBriefRepository(session).get_revision(*key, actor_id=owner)
            row = await session.get(ResearchBriefRevisionRow, key)
            assert row is not None
            value = json.loads(row.payload)
            value["unexpected"] = {"nested": {"untrusted": True}}
            payload = json.dumps(
                value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
            )
            encoded = payload.encode("utf-8")
            row.payload = payload
            row.payload_sha256 = hashlib.sha256(encoded).hexdigest()
            row.payload_bytes = len(encoded)
            await session.commit()
        async with maker() as session:
            with pytest.raises(Conflict, match="validation"):
                await SqlResearchBriefRepository(session).get_revision(*key, actor_id=owner)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_revision_chain_cannot_change_owner_or_skip_a_version() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        maker = async_sessionmaker(engine, expire_on_commit=False)
        owner = uuid4()
        brief = _brief(owner_id=owner)
        async with maker() as session:
            repo = SqlResearchBriefRepository(session)
            await repo.add_revision(brief, actor_id=owner)
            changed = brief.revise(at=NOW + timedelta(minutes=1))
            other_owner = uuid4()
            with pytest.raises(Conflict):
                await repo.add_revision(
                    replace(changed, identity=replace(changed.identity, owner_id=other_owner)),
                    actor_id=other_owner,
                )
            with pytest.raises(Conflict):
                await repo.add_revision(
                    replace(changed, identity=replace(changed.identity, revision=3)),
                    actor_id=owner,
                )
            with pytest.raises(Conflict):
                await repo.add_revision(
                    replace(changed, identity=replace(changed.identity, revised_at=NOW)),
                    actor_id=owner,
                )
    finally:
        await engine.dispose()
