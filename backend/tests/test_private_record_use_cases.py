"""Private-record policy is testable without a web app, session or SQL repository."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from ase.application.access import AccessContext
from ase.application.assistant_history.manage import ManageAssistantHistory
from ase.application.research.manage_briefs import BriefScopeChange, ManageResearchBriefs
from ase.domain.errors import Conflict, Forbidden, NotFound
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
from ase.domain.users import Role, User

NOW = datetime(2026, 9, 20, tzinfo=UTC)


def actor(role=Role.USER):
    return User(uuid4(), "actor@example.org", "Actor", role, True, None, 0, None, None, NOW, None)


def definition(identity):
    return ResearchBrief(
        identity=identity,
        question=BriefQuestion(main="What changed?"),
        scope=BriefScope(),
        observation=BriefObservation(policy="template_default"),
        lens=BriefLens(),
        collection=BriefCollection(),
        output=BriefOutput(depth=ResearchMode.QUICK),
        limits=BriefLimits(),
        monitoring=BriefMonitoring(),
    )


def brief_service(owner):
    identity = BriefIdentity(uuid4(), 1, owner.id, "Saved brief", NOW, NOW)
    brief = definition(identity)
    repository = SimpleNamespace(
        visible=AsyncMock(return_value=brief),
        list_visible=AsyncMock(return_value=[identity]),
        add_revision=AsyncMock(side_effect=lambda value, **kwargs: value),
    )
    context = AccessContext(owner, {}, {})
    access = SimpleNamespace(context=AsyncMock(return_value=context))
    uow = SimpleNamespace(commit=AsyncMock())
    service = ManageResearchBriefs(repository, access, SimpleNamespace(now=lambda: NOW), uow)
    draft = SimpleNamespace(
        title="Revised brief",
        team_id=None,
        preset_id=None,
        preset_version=None,
        to_brief=definition,
    )
    return service, repository, access, uow, draft, brief


async def test_brief_revision_is_owner_only_even_for_admin():
    admin = actor(Role.ADMIN)
    service, repository, _, uow, draft, brief = brief_service(admin)
    repository.visible.return_value = replace(
        brief, identity=replace(brief.identity, owner_id=uuid4())
    )
    with pytest.raises(Forbidden, match="Only the Research Brief owner"):
        await service.revise(admin, brief.identity.id, 1, draft)
    repository.add_revision.assert_not_awaited()
    uow.commit.assert_not_awaited()


async def test_brief_revision_rejects_scope_change_and_stale_revision_before_write():
    owner = actor()
    service, repository, _, _, draft, brief = brief_service(owner)
    draft.team_id = uuid4()
    with pytest.raises(BriefScopeChange):
        await service.revise(owner, brief.identity.id, 1, draft)
    draft.team_id = None
    with pytest.raises(Conflict, match="newer revision"):
        await service.revise(owner, brief.identity.id, 2, draft)
    repository.add_revision.assert_not_awaited()


async def test_brief_revision_uses_locked_access_and_monotonic_time_without_early_commit():
    owner = actor()
    service, repository, access, uow, draft, brief = brief_service(owner)
    saved = await service.revise(owner, brief.identity.id, 1, draft)
    assert saved.identity.revision == 2
    assert saved.identity.revised_at == NOW + timedelta(microseconds=1)
    assert saved.identity.created_at == NOW
    access.context.assert_awaited_once_with(owner, for_update=True)
    repository.add_revision.assert_awaited_once()
    uow.commit.assert_not_awaited()
    await service.commit()
    uow.commit.assert_awaited_once()


async def test_brief_lists_pass_current_visibility_and_missing_history_does_not_list():
    owner = actor()
    service, repository, access, _, _, brief = brief_service(owner)
    await service.list(owner, 3, 7)
    repository.list_visible.assert_awaited_once_with(
        access.context.return_value.visibility, 3, 7, None
    )
    repository.list_visible.reset_mock()
    repository.visible.return_value = None
    with pytest.raises(NotFound):
        await service.list(owner, 3, 7, brief.identity.id)
    repository.list_visible.assert_not_awaited()


async def test_conversation_report_access_failure_prevents_both_create_and_replace():
    owner = actor()
    repository = SimpleNamespace(create=AsyncMock(), update=AsyncMock())
    reports = SimpleNamespace(execute=AsyncMock(side_effect=NotFound()))
    clock = SimpleNamespace(now=Mock(return_value=NOW))
    uow = SimpleNamespace(commit=AsyncMock())
    service = ManageAssistantHistory(repository, reports, clock, uow)
    reference = (uuid4(), 2)
    for conversation_id in (None, uuid4()):
        with pytest.raises(NotFound):
            await service.save(owner, "Notes", [], [reference], conversation_id)
    repository.create.assert_not_awaited()
    repository.update.assert_not_awaited()
    uow.commit.assert_not_awaited()


async def test_conversation_rechecks_exact_distinct_report_editions():
    owner = actor()
    report_id = uuid4()
    reports = SimpleNamespace(execute=AsyncMock())
    service = ManageAssistantHistory(Mock(), reports, Mock(), Mock())
    await service.authorise_reports(owner, [(report_id, 1), (report_id, 1), (report_id, 2)])
    assert reports.execute.await_count == 2
    reports.execute.assert_any_await(owner, report_id, 1)
    reports.execute.assert_any_await(owner, report_id, 2)
