"""Visibility precedes pagination; commit and release retain the session boundary."""

from dataclasses import replace
from datetime import timedelta

from sqlalchemy import func, select

from ase.adapters.persistence.research_brief_models import ResearchBriefRevisionRow
from ase.adapters.persistence.research_briefs import SqlResearchBriefRepository
from ase.application.research.manage_briefs import ManageResearchBriefs
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token
from test_research_brief_api import _draft
from test_research_brief_persistence import _brief


async def test_brief_visibility_filters_hidden_latest_before_limit_and_offset(
    container, user, admin
):
    older, newer = _brief(owner_id=user.id), _brief(owner_id=user.id)
    newer = replace(
        newer,
        identity=replace(
            newer.identity, revised_at=newer.identity.revised_at + timedelta(seconds=1)
        ),
    )
    hidden = _brief(owner_id=admin.id)
    hidden = replace(
        hidden,
        identity=replace(
            hidden.identity, revised_at=hidden.identity.revised_at + timedelta(seconds=2)
        ),
    )
    async with container.session_factory() as session:
        repository = SqlResearchBriefRepository(session)
        for brief in (older, newer, hidden):
            await repository.add_revision(brief, actor_id=brief.identity.owner_id)
        await session.commit()
        service = container.research_briefs(session)
        assert [item.id for item in await service.list(user, 1, 0)] == [newer.identity.id]
        assert [item.id for item in await service.list(user, 1, 1)] == [older.identity.id]
        assert await service.list(user, 1, 2) == []


async def test_brief_expiry_before_commit_rolls_back_private_write(
    client, user, container, clock, monkeypatch
):
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    expiry = container.issuer.verify(token).expires_at
    original = SqlResearchBriefRepository.add_revision

    async def expire_before_commit(self, *args, **kwargs):
        result = await original(self, *args, **kwargs)
        clock.advance(expiry - clock.now() + timedelta(seconds=1))
        return result

    monkeypatch.setattr(SqlResearchBriefRepository, "add_revision", expire_before_commit)
    draft = {**_draft(), "title": "PRIVATE BRIEF CONTENT"}
    response = await client.post("/api/research/briefs", json=draft, headers=bearer(token))
    assert response.status_code == 401
    assert "PRIVATE BRIEF CONTENT" not in response.text
    async with container.session_factory() as session:
        count = await session.scalar(select(func.count()).select_from(ResearchBriefRevisionRow))
        assert count == 0


async def test_brief_revocation_after_commit_blocks_private_response(
    client, user, container, clock, monkeypatch
):
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    original = ManageResearchBriefs.commit

    async def revoke_after_commit(self):
        await original(self)
        async with container.session_factory() as session:
            repos = container.repositories(session)
            await repos.refresh_tokens.revoke_all_for_user(user.id, clock.now())
            await repos.uow.commit()

    monkeypatch.setattr(ManageResearchBriefs, "commit", revoke_after_commit)
    draft = {**_draft(), "title": "PRIVATE BRIEF CONTENT"}
    response = await client.post("/api/research/briefs", json=draft, headers=bearer(token))
    assert response.status_code == 401
    assert "PRIVATE BRIEF CONTENT" not in response.text
    async with container.session_factory() as session:
        count = await session.scalar(select(func.count()).select_from(ResearchBriefRevisionRow))
        assert count == 1
