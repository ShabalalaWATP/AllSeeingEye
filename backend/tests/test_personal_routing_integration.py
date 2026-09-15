"""Saved owner routing is retained through administrator regeneration and schedules."""

from dataclasses import replace
from unittest.mock import AsyncMock
from uuid import uuid4

from ase.application.dto import RequestContext
from ase.application.reports.request import ReportRequest
from ase.application.schedules.report_request import scheduled_report_request
from ase.domain.llm import LlmConnectionBinding, LlmResult
from ase.domain.schedules import Schedule
from test_claim_repository import seed
from test_generate_claims import output_for
from test_model_routing import profile
from test_model_routing_integration import Gateway, setup_routing
from test_saved_map_views import claims_for


async def personal_setup(container, admin, user):
    first, second, existing = await setup_routing(container, admin, user)
    person = profile("personal-model")
    person.api_key_encrypted = container.cipher.encrypt("fixture-" + person.model)
    async with container.session_factory() as session:
        repos = container.repositories(session)
        await repos.llm_profiles.add(person)
        for owner, value in ((user.id, person), (admin.id, existing[1])):
            await repos.llm_bindings.save(
                LlmConnectionBinding(
                    None,
                    value.id,
                    value.revision,
                    value.config_hash,
                    container.clock.now(),
                    admin.id,
                    user_id=owner,
                )
            )
        await session.commit()
    return first, second, person, existing


async def test_admin_regeneration_uses_personal_report_owner_not_admin(container, admin, user):
    _, _, person, _ = await personal_setup(container, admin, user)
    container.llm = Gateway()
    async with container.session_factory() as session:
        record, version = await container.generate_report(session).execute(
            user, ReportRequest("ask", question="Will fighting increase?"), RequestContext()
        )
    assert version.model_routing.binding_user_id == user.id
    container.llm = gateway = Gateway()
    async with container.session_factory() as session:
        _, updated = await container.generate_report(session).regenerate(
            admin, record.id, RequestContext()
        )
    assert {call[0] for call in gateway.calls} == {person.model}
    assert updated.model_routing.binding_user_id == user.id


async def test_personal_schedule_and_shared_translation_are_isolated(container, admin, user):
    first, second, person, values = await personal_setup(container, admin, user)
    now = container.clock.now()
    schedule = Schedule(
        uuid4(),
        "Personal morning",
        "intsum",
        None,
        None,
        6,
        "daily",
        0,
        None,
        True,
        user.id,
        now,
        now,
    )
    for team_id, expected in ((None, person), (first.id, values[1]), (second.id, values[0])):
        container.llm = gateway = Gateway()
        async with container.session_factory() as session:
            await container.generate_report(session).execute(
                user,
                scheduled_report_request(replace(schedule, id=uuid4(), team_id=team_id)),
                RequestContext(),
            )
        assert {call[0] for call in gateway.calls} == {expected.model}
    assert (await container._translation_profile()).id == values[0].id


async def test_admin_claim_generation_uses_destination_owner(client, container, admin, user):
    _, _, person, _ = await personal_setup(container, admin, user)
    report, version, _ = await seed(container, user)
    actor = await claims_for(client, container, admin)
    async with container.session_factory() as session:
        service = container.generate_claims(session)
        service.gateway = gateway = AsyncMock()
        gateway.complete.return_value = LlmResult(output_for(version), "returned-model", 5, 10, 20)
        result = await service.execute(actor, report.id, 1, RequestContext())
    assert result.status == "completed"
    assert gateway.complete.call_args.args[2] == person.model
    assert result.items[0].model_origin.profile_id == person.id
