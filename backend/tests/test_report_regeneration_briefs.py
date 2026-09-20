"""Regeneration consumes and retains the exact authored task of the frozen version."""

from dataclasses import replace
from uuid import uuid4

import pytest

from ase.application.dto import RequestContext
from ase.application.reports.request import ReportRequest
from ase.domain.research import ResearchFocus, ResearchMode
from ase.domain.research_brief_values import IntelligenceRequirement
from llm_fixture_helpers import seed_legacy_profile
from report_helpers import PROFILE
from report_input_helpers import CallbackGateway, NoPublicCollection, saved_parent


@pytest.mark.parametrize("authored", [True, False])
async def test_regeneration_keeps_frozen_requirements_and_brief_provenance(
    container, user, authored
):
    await seed_legacy_profile(container, {**PROFILE, "roles": ["assessment", "direction"]})
    record, previous = await saved_parent(container, user)
    requirements = (
        IntelligenceRequirement("IR-transport", "Which transport links were disrupted?"),
    )
    previous = replace(
        previous,
        canonical_requirements=requirements if authored else (),
        brief_id=uuid4() if authored else None,
        brief_revision=3 if authored else None,
    )
    # Store the frozen version as an independent report; no current brief is needed
    # to reproduce the exact task which the authorised report already contains.
    async with container.session_factory() as session:
        repository = container.repositories(session).reports
        await repository.delete(record.id)
        await repository.add(record, previous)
        await session.commit()
    gateway = CallbackGateway()
    container.llm = gateway
    container.research = NoPublicCollection()
    async with container.session_factory() as session:
        _, generated = await container.generate_report(session).regenerate(
            user, record.id, RequestContext()
        )
    if authored:
        assert any(
            requirements[0].question in message.content
            for request in gateway.requests
            for message in request.messages
        )
    assert generated.canonical_requirements == previous.canonical_requirements
    assert (generated.brief_id, generated.brief_revision) == (
        previous.brief_id,
        previous.brief_revision,
    )
    async with container.session_factory() as session:
        saved = await container.repositories(session).reports.get_version(record.id, 2)
        assert saved.canonical_requirements == previous.canonical_requirements
        assert (saved.brief_id, saved.brief_revision) == (
            previous.brief_id,
            previous.brief_revision,
        )


async def test_ordinary_followup_does_not_claim_the_parent_brief(container, user):
    await seed_legacy_profile(container, {**PROFILE, "roles": ["assessment", "direction"]})
    record, previous = await saved_parent(container, user)
    previous = replace(previous, brief_id=uuid4(), brief_revision=3)
    async with container.session_factory() as session:
        repository = container.repositories(session).reports
        await repository.delete(record.id)
        await repository.add(record, previous)
        await session.commit()
    container.llm = CallbackGateway()
    container.research = NoPublicCollection()
    async with container.session_factory() as session:
        child, generated = await container.generate_report(session).execute(
            user,
            ReportRequest(
                "ask",
                question="What else can the saved evidence establish?",
                research_mode=ResearchMode.QUICK,
                research_focus=ResearchFocus.DOCUMENT,
                parent_report_id=record.id,
                parent_version=1,
            ),
            RequestContext(),
        )
    assert child.id != record.id
    assert generated.number == 1
    assert generated.evidence
    assert (generated.brief_id, generated.brief_revision) == (None, None)
    async with container.session_factory() as session:
        saved = await container.repositories(session).reports.get_version(child.id, 1)
        assert (saved.brief_id, saved.brief_revision) == (None, None)
