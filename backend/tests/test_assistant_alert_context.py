"""Alert samples remain scoped, bounded and explicit about current evidence gaps."""

import json
from dataclasses import replace
from uuid import uuid4

import pytest

from ai_usage_helpers import add_policy, policy, reservations
from ase.adapters.persistence.warning_mapping import _alert_row
from ase.api.schemas_assistant import AssistantAnswerIn, AssistantAnswerOut
from ase.domain.ai_usage import AiAllowanceExceeded, AiPolicyScope
from ase.domain.assistant import AssistantQuestion
from ase.domain.errors import InvalidRequest, NotFound
from ase.domain.warning import Alert
from assistant_helpers import Admission, Gateway, event, nothing, profile
from helpers import USER_PASSWORD, create_user
from team_helpers import CONTEXT, team_service
from warning_scope_helpers import create_indicator
from warning_scope_helpers import warning_actors as warning_actors  # noqa: PLC0414


async def seed(container, user, *, ids=("quake",), team_id=None, count=300):
    container.source_admission = Admission()
    container.llm = Gateway()
    rule = await create_indicator(container, user, team_id)
    alert = Alert(
        uuid4(),
        rule.id,
        container.clock.now(),
        "Scoped alert",
        "",
        count,
        1,
        ids,
        (),
        created_by=user.id,
        team_id=team_id,
    )
    async with container.session_factory() as session:
        session.add(_alert_row(alert))
        await session.commit()
    return alert


async def ask(container, user, alert):
    async with container.session_factory() as session:
        return await container.map_assistant(session).execute(
            user,
            AssistantQuestion("Explain this alert", scope="alert", alert_id=alert.id),
            check_session=nothing,
        )


async def test_partial_sample_and_changed_records_are_explicit(container, user):
    alert = await seed(container, user, ids=("quake", "missing", "disabled"))
    await profile(container)
    container.store.upsert(
        (event(title="Corrected earthquake record"), event("disabled", source="disabled_source"))
    )
    container.source_admission.disabled.add("disabled_source")
    answer = await ask(container, user, alert)
    assert [row.title for row in answer.context.sources] == ["Corrected earthquake record"]
    assert answer.continuation_id is None
    assert answer.context.alert.matched_count == 300
    assert answer.context.alert.stored_sample_size == 3
    assert answer.context.alert.available_evidence_count == 1
    assert "not an immutable" in answer.context.notes[0]
    packet = json.loads(container.llm.calls[0].messages[1].content)
    assert packet["alert"]["matched_count"] == 300
    assert len(packet["context"]["sources"]) == 1
    output = AssistantAnswerOut.from_answer(answer).model_dump()
    assert set(output["alert"]) == {
        "id",
        "matched_count",
        "stored_sample_size",
        "available_evidence_count",
    }


@pytest.mark.parametrize("ids", [(), ("missing",), ("disabled",)])
async def test_unusable_context_never_calls_model_or_searches_globally(container, user, ids):
    alert = await seed(container, user, ids=ids)
    container.store.upsert((event(), event("disabled", source="disabled_source")))
    container.source_admission.disabled.add("disabled_source")
    answer = await ask(container, user, alert)
    assert not container.llm.calls and answer.model is None
    assert not answer.context.sources
    assert "no usable retained event references" in answer.paragraphs[0].text


async def test_personal_alert_is_not_disclosed_to_another_actor(container, user):
    alert = await seed(container, user)
    other = await create_user(container, email="other-alert@example.test", password=USER_PASSWORD)
    with pytest.raises(NotFound):
        await ask(container, other, alert)
    assert not container.llm.calls


@pytest.mark.parametrize("change", ["membership", "source"])
async def test_team_access_or_source_revocation_prevents_release(
    container,
    admin,
    warning_actors,
    change,
):
    actors = warning_actors
    alert = await seed(container, actors.owner, team_id=actors.team.id)
    await profile(container)
    container.store.upsert((event(),))

    async def revoke():
        if change == "source":
            container.source_admission.disabled.add("usgs_earthquakes")
        else:
            async with team_service(container) as service:
                await service.remove_member(admin, actors.team.id, actors.peer.id, CONTEXT)

    container.llm.after = revoke
    with pytest.raises(NotFound if change == "membership" else InvalidRequest):
        await ask(container, actors.peer, alert)
    assert len(container.llm.calls) == 1


async def test_cannot_cite_an_unavailable_reference(container, user):
    alert = await seed(container, user, ids=("quake", "missing"))
    await profile(container)
    container.store.upsert((event(),))
    container.llm.content = json.dumps(
        {
            "paragraphs": [
                {"kind": "finding", "text": "Unsupported claim", "citations": ["E2"]},
            ]
        }
    )
    with pytest.raises(InvalidRequest, match="unsupported"):
        await ask(container, user, alert)


async def test_team_allowance_is_charged_once_then_prevents_provider_dispatch(
    container, warning_actors
):
    actors = warning_actors
    alert = await seed(container, actors.owner, team_id=actors.team.id)
    await profile(container)
    container.store.upsert((event(),))
    await add_policy(
        container, policy(limit=1, tokens=None, scope=AiPolicyScope.TEAM, target_id=actors.team.id)
    )
    await ask(container, actors.peer, alert)
    with pytest.raises(AiAllowanceExceeded):
        await ask(container, actors.peer, alert)
    assert len(container.llm.calls) == 1
    rows = await reservations(container)
    assert rows[0].user_id == actors.peer.id and rows[0].team_id == actors.team.id


def test_alert_scope_rejects_ambiguous_context():
    for extra in (
        {},
        {"time_range": {"since": "2026-01-01T00:00:00Z", "until": "2026-01-02T00:00:00Z"}},
        {"continuation_id": "a" * 20},
    ):
        body = {"question": "Explain", "scope": "alert"}
        if extra:
            body["alert_id"] = str(uuid4())
            body.update(extra)
        with pytest.raises(ValueError):
            AssistantAnswerIn(**body)
    question = AssistantQuestion("Explain", scope="alert", alert_id=uuid4())
    with pytest.raises(ValueError):
        replace(question, scope="global")
