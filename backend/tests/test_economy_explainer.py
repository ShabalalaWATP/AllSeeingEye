"""Cadence, admission, metering and the honest states of the economy explainer."""

from __future__ import annotations

import asyncio
import json
from datetime import timedelta

from sqlalchemy import func, select

from ai_usage_helpers import add_policy, policy, reservations
from ase.adapters.persistence.economy_explainer_models import EconomyExplainerRow
from ase.application.economy_explainer_facts import build_fact_pack, fingerprint
from ase.application.ports.llm import LlmGatewayError
from ase.domain.ai_usage import AiPolicyScope, AiReservationStatus
from ase.domain.llm import LlmResult
from economy_explainer_helpers import (
    content,
    explainer_profile,
    headline,
    install,
    payload,
    snapshot,
)


class ScriptedGateway:
    """Returns each scripted answer in turn and records every request it was sent."""

    def __init__(self, *answers: str) -> None:
        self.answers = list(answers)
        self.requests: list[object] = []
        self.error: Exception | None = None
        self.tokens = (900, 400)

    async def complete(self, base_url, key, model, request):
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        answer = self.answers.pop(0) if self.answers else content()
        return LlmResult(answer, "economy-fixture-model", 11.0, *self.tokens)


async def read(container, *, allow_generation: bool = True):
    async with container.session_factory() as session:
        return await container.economy_explainer(session).read(allow_generation=allow_generation)


async def refresh(container):
    async with container.session_factory() as session:
        return await container.economy_explainer(session).refresh()


async def setup(container, monkeypatch, gateway=None, **kwargs):
    install(container, monkeypatch, **kwargs)
    await explainer_profile(container)
    container.llm = gateway or ScriptedGateway()
    return container.llm


async def test_nothing_generated_yet_is_reported_honestly_without_a_model_call(
    container, monkeypatch
):
    install(container, monkeypatch)
    gateway = ScriptedGateway()
    container.llm = gateway
    view = await read(container, allow_generation=False)
    assert (view.status, view.explainer) == ("empty", None)
    assert "at most once a day" in (view.reason or "")
    assert gateway.requests == []


async def test_one_generation_serves_every_later_reader_for_the_same_figures(
    container, monkeypatch
):
    gateway = await setup(container, monkeypatch)
    first = await read(container)
    assert first.status == "ready" and first.explainer is not None
    assert first.explainer.model == "economy-fixture-model"
    assert first.explainer.prompt_tokens == 900
    second = await read(container)
    assert second.status == "ready"
    # A second reader is served the stored text; only one model call was ever made.
    assert len(gateway.requests) == 1
    assert second.explainer is not None
    assert second.explainer.generated_at == first.explainer.generated_at


async def test_moved_figures_are_marked_stale_until_a_day_has_passed(container, monkeypatch):
    gateway = await setup(container, monkeypatch)
    await read(container)
    # New dated headlines move the fact pack on without changing any figure.
    install(container, monkeypatch, headlines=2)
    stale = await read(container)
    assert (stale.status, stale.stale) == ("stale", True)
    assert stale.explainer is not None and len(gateway.requests) == 1
    container.clock.advance(timedelta(hours=24))
    fresh = await read(container)
    assert (fresh.status, fresh.stale) == ("ready", False)
    assert len(gateway.requests) == 2


async def test_only_the_latest_two_rows_are_kept(container, monkeypatch):
    await setup(container, monkeypatch)
    for index in (1, 2, 3):
        install(container, monkeypatch, headlines=index)
        container.clock.advance(timedelta(hours=25))
        await read(container)
    async with container.session_factory() as session:
        total = await session.scalar(select(func.count()).select_from(EconomyExplainerRow))
    assert total == 2


async def test_a_second_request_during_generation_is_told_a_summary_is_being_written(
    container, monkeypatch
):
    gateway = await setup(container, monkeypatch)
    entered, release = asyncio.Event(), asyncio.Event()
    original = gateway.complete

    async def slow(*args, **kwargs):
        entered.set()
        await release.wait()
        return await original(*args, **kwargs)

    gateway.complete = slow  # type: ignore[method-assign]
    first = asyncio.create_task(read(container))
    await entered.wait()
    busy = await read(container)
    assert (busy.status, busy.explainer) == ("generating", None)
    release.set()
    assert (await first).status == "ready"


async def test_a_rejected_answer_is_retried_once_with_the_reasons_and_then_discarded(
    container, monkeypatch
):
    invented = content(
        world={
            **payload()["world"],  # type: ignore[dict-item]
            "paragraphs": ["Growth reached 9.9% in 2024.", "Prices rose by 3% in 2024."],
        }
    )
    gateway = await setup(container, monkeypatch, ScriptedGateway(invented, invented))
    view = await read(container)
    assert view.status == "validation_failed" and view.explainer is None
    assert "failed the automatic checks" in (view.reason or "")
    assert len(gateway.requests) == 2
    assert "9.9 does not match" in gateway.requests[1].messages[1].content
    # Nothing that failed the checks may reach the database.
    assert (await read(container, allow_generation=False)).status == "empty"


async def test_a_retry_that_passes_is_stored(container, monkeypatch):
    invented = content(
        world={
            **payload()["world"],  # type: ignore[dict-item]
            "paragraphs": ["Growth reached 9.9% in 2024.", "Prices rose by 3% in 2024."],
        }
    )
    gateway = await setup(container, monkeypatch, ScriptedGateway(invented, content()))
    view = await read(container)
    assert view.status == "ready" and len(gateway.requests) == 2


async def test_no_assigned_model_reports_an_honest_empty_state(container, monkeypatch):
    install(container, monkeypatch)
    container.llm = ScriptedGateway()
    view = await read(container)
    assert view.status == "unavailable"
    assert "No model is available" in (view.reason or "")


async def test_a_spent_allowance_reports_the_reason_and_never_an_error(container, monkeypatch):
    await setup(container, monkeypatch)
    await add_policy(container, policy(limit=0, tokens=None, scope=AiPolicyScope.SYSTEM))
    view = await read(container)
    assert view.status == "unavailable"
    assert "allowance is spent" in (view.reason or "")


async def test_a_provider_failure_reports_the_reason(container, monkeypatch):
    gateway = await setup(container, monkeypatch)
    gateway.error = LlmGatewayError("endpoint refused")
    view = await read(container)
    assert view.status == "unavailable"
    assert "could not be reached" in (view.reason or "")


async def test_the_call_is_reserved_and_settled_against_the_system_budget(container, monkeypatch):
    await setup(container, monkeypatch)
    await add_policy(container, policy(limit=5, tokens=None, scope=AiPolicyScope.SYSTEM))
    await read(container)
    [row] = await reservations(container)
    assert row.status is AiReservationStatus.SETTLED
    assert row.attribution.system is True and row.attribution.user_id is None
    assert row.purpose == "economy_explainer"
    assert (row.prompt_tokens, row.completion_tokens) == (900, 400)


async def test_the_stored_row_carries_provenance_but_never_a_prompt(container, monkeypatch):
    await setup(container, monkeypatch)
    view = await read(container)
    assert view.explainer is not None
    assert view.explainer.snapshot_fetched_at == snapshot().fetched_at
    assert view.explainer.fingerprint == fingerprint(build_fact_pack(snapshot(), (headline(),)))
    async with container.session_factory() as session:
        row = await session.scalar(select(EconomyExplainerRow))
    assert row is not None
    stored = json.dumps(row.payload)
    assert "Facts:" not in stored and "British English" not in stored


async def test_an_administrator_refresh_ignores_the_daily_cadence(container, monkeypatch):
    gateway = await setup(container, monkeypatch)
    await read(container)
    install(container, monkeypatch, headlines=2)
    assert (await read(container)).status == "stale"
    assert len(gateway.requests) == 1
    forced = await refresh(container)
    assert (forced.status, forced.stale) == ("ready", False)
    assert len(gateway.requests) == 2
