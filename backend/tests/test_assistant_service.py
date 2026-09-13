"""Request-local model routing, source/session release checks and operational accounting."""

import asyncio
from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest

from ase.application.assistant.service import AssistantCapacity
from ase.application.ports.llm import LlmTokenBudgetExhausted
from ase.domain.assistant import AssistantQuestion
from ase.domain.errors import InvalidRequest, RateLimited, Unauthenticated
from ase.domain.llm import ReasoningEffort
from assistant_helpers import Admission, Gateway, event, nothing, profile


async def setup(container):
    chosen = await profile(container)
    gateway = Gateway()
    container.llm = gateway
    container.source_admission = Admission()
    container.store.upsert((event(),))
    return chosen, gateway


async def test_one_call_uses_current_profile_as_of_and_stores_only_usage(container, user):
    chosen, gateway = await setup(container)
    async with container.session_factory() as session:
        answer = await container.map_assistant(session).execute(
            user,
            AssistantQuestion("Recent earthquakes"),
            check_session=nothing,
        )
    assert len(gateway.calls) == 1
    request = gateway.calls[0]
    assert request.reasoning_effort is ReasoningEffort.MAX and request.max_output_tokens == 32000
    assert container.clock.now().isoformat() in request.messages[1].content
    assert answer.model.reasoning_effort == "max" and answer.context.sources[0].id == "E1"
    async with container.session_factory() as session:
        usages = await container.repositories(session).llm_usage.list_recent(5)
    assert (
        len(usages) == 1
        and usages[0].profile_id == chosen.id
        and usages[0].purpose == "map_assistant"
    )
    assert usages[0].prompt_tokens == 100 and usages[0].completion_tokens == 50
    assert usages[0].error is None


async def test_empty_scope_does_not_require_or_call_model(container, user):
    gateway = Gateway()
    container.llm = gateway
    async with container.session_factory() as session:
        answer = await container.map_assistant(session).execute(
            user,
            AssistantQuestion("earthquakes near Atlantis"),
            check_session=nothing,
        )
    assert answer.model is None and not answer.context.sources and not gateway.calls
    assert answer.paragraphs[0].kind == "gap"


@pytest.mark.parametrize("change", ["source", "session"])
async def test_source_or_session_revoked_during_bookkeeping_prevents_release(
    change, container, user
):
    await setup(container)
    started, release = asyncio.Event(), asyncio.Event()
    live = True
    saved = []

    async def sink(usage):
        started.set()
        await release.wait()
        saved.append(usage)

    async def check():
        if not live:
            raise Unauthenticated()

    async with container.session_factory() as session:
        service = container.map_assistant(session)
        service.record_usage = sink
        task = asyncio.create_task(
            service.execute(user, AssistantQuestion("earthquakes"), check_session=check)
        )
        await started.wait()
        if change == "source":
            container.source_admission.disabled.add("usgs_earthquakes")
        else:
            live = False
        release.set()
        with pytest.raises(InvalidRequest if change == "source" else Unauthenticated):
            await task
    assert len(saved) == 1 and not container.assistant_capacity.active


@pytest.mark.parametrize("storage_failure", [False, True])
async def test_cancellation_during_bookkeeping_keeps_one_bounded_writer(
    container, user, storage_failure
):
    await setup(container)
    started, release = asyncio.Event(), asyncio.Event()
    saved = []

    async def sink(usage):
        started.set()
        await release.wait()
        saved.append(usage)
        if storage_failure:
            raise OSError("Synthetic close failure after cancellation and commit")

    async with container.session_factory() as session:
        service = container.map_assistant(session)
        service.record_usage = sink
        task = asyncio.create_task(
            service.execute(user, AssistantQuestion("earthquakes"), check_session=nothing)
        )
        await started.wait()
        task.cancel()
        await asyncio.sleep(0)
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert len(saved) == 1 and not container.assistant_capacity.active


async def test_uncertain_commit_is_not_retried_and_known_counts_are_sanitised(container, user):
    _, gateway = await setup(container)
    gateway.tokens = (True, -30)
    saved = []

    async def sink(usage):
        saved.append(usage)
        raise OSError("Synthetic close error after commit")

    async with container.session_factory() as session:
        service = container.map_assistant(session)
        service.record_usage = sink
        answer = await service.execute(
            user, AssistantQuestion("earthquakes"), check_session=nothing
        )
    assert len(saved) == 1 and saved[0].prompt_tokens is saved[0].completion_tokens is None
    assert any("Usage storage unconfirmed" in note for note in answer.context.notes)


@pytest.mark.parametrize("failure", ["exhausted", "invalid"])
async def test_failed_output_retains_known_usage_without_retry(failure, container, user):
    _, gateway = await setup(container)
    if failure == "exhausted":
        gateway.error = LlmTokenBudgetExhausted(
            model="fixture", prompt_tokens=12, completion_tokens=32000
        )
    else:
        gateway.content = '{"paragraphs":[]}'
    async with container.session_factory() as session:
        with pytest.raises(InvalidRequest):
            await container.map_assistant(session).execute(
                user,
                AssistantQuestion("earthquakes"),
                check_session=nothing,
            )
    async with container.session_factory() as session:
        saved = await container.repositories(session).llm_usage.list_recent(5)
    assert len(gateway.calls) == len(saved) == 1 and not saved[0].ok
    assert saved[0].prompt_tokens == (12 if failure == "exhausted" else 100)


async def test_scope_and_current_actor_access_are_checked_before_disclosure(container, user):
    _, gateway = await setup(container)
    async with container.session_factory() as session:
        with pytest.raises(Unauthenticated):
            await container.map_assistant(session).execute(
                replace(user, security_version=user.security_version + 1),
                AssistantQuestion("earthquakes"),
                check_session=nothing,
            )
    assert not gateway.calls


async def test_followup_uses_same_users_frozen_evidence_and_rechecks_source(container, user):
    _, gateway = await setup(container)
    async with container.session_factory() as session:
        first = await container.map_assistant(session).execute(
            user, AssistantQuestion("earthquakes"), check_session=nothing
        )
    assert first.continuation_id
    async with container.session_factory() as session:
        second = await container.map_assistant(session).execute(
            user,
            AssistantQuestion(
                "Which of those are independently confirmed?",
                continuation_id=first.continuation_id,
            ),
            check_session=nothing,
        )
    assert [row.record_id for row in second.context.sources] == ["quake"]
    assert "frozen evidence" in " ".join(second.context.notes)
    assert len(gateway.calls) == 2
    container.source_admission.disabled.add("usgs_earthquakes")
    async with container.session_factory() as session:
        with pytest.raises(InvalidRequest, match="disabled"):
            await container.map_assistant(session).execute(
                user,
                AssistantQuestion("Which of those?", continuation_id=first.continuation_id),
                check_session=nothing,
            )
    assert len(gateway.calls) == 2


async def test_continuation_expires_and_is_bound_to_security_version(container, user):
    capacity = AssistantCapacity()
    _, gateway = await setup(container)
    async with container.session_factory() as session:
        first = await container.map_assistant(session).execute(
            user, AssistantQuestion("earthquakes"), check_session=nothing
        )
    context = first.context
    token = capacity.remember(user, context, container.clock.now())
    assert capacity.find(user, token, container.clock.now()) == context
    assert (
        capacity.find(
            replace(user, security_version=user.security_version + 1), token, container.clock.now()
        )
        is None
    )
    container.clock.advance(timedelta(minutes=21))
    assert capacity.find(user, token, container.clock.now()) is None
    async with container.session_factory() as session:
        with pytest.raises(InvalidRequest, match="expired"):
            await container.map_assistant(session).execute(
                user,
                AssistantQuestion("Which of those?", continuation_id=first.continuation_id),
                check_session=nothing,
            )
    assert len(gateway.calls) == 1


def test_capacity_blocks_duplicate_user_and_global_saturation(user):
    capacity = AssistantCapacity(1)
    with capacity.reserve(user.id):
        for actor_id in (user.id, uuid4()):
            with pytest.raises(RateLimited), capacity.reserve(actor_id):
                pass
    assert not capacity.active
