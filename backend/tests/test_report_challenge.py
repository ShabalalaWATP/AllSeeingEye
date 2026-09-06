"""Every-judgement challenge remains bounded and distinguishable from verification."""

import json
from dataclasses import replace
from unittest.mock import AsyncMock

import pytest

from ase.application.reports.advocacy import apply_advocacy
from ase.application.reports.challenge import run_challenge
from ase.application.reports.challenge_models import challenge_call, parse_plans, parse_reviews
from ase.application.reports.drafting import Draft
from ase.application.reports.production_types import Totals
from ase.application.reports.selection import Selection
from ase.domain.advocacy import DevilsAdvocacy
from ase.domain.doctrine import Confidence
from ase.domain.errors import RateLimited
from ase.domain.llm import LlmResult
from ase.domain.reports import parse_body
from ase.domain.research import (
    CollectionAttempt,
    CollectionStatus,
    ResearchBatch,
    ResearchFocus,
    ResearchQuery,
)
from ase.domain.validation import Finding, Severity
from feeds_helpers import make_event
from production_integration_helpers import production_job
from report_documents_helpers import document_records
from report_helpers import ScriptedGateway, filled_store, good_body


def plans():
    return {
        "judgements": [
            {"target": key, "terms": [f"{key} ceasefire alternative"]} for key in ("KJ1", "KJ2")
        ]
    }


def reviews():
    return {
        "judgements": [
            {
                "target": key,
                "argument": "Routine activity could explain the report.",
                "evidence": ["E1"],
                "lower_confidence": True,
                "rationale": "The evidence is one-sided.",
            }
            for key in ("KJ1", "KJ2")
        ]
    }


def test_advocacy_lowers_its_named_target_only():
    body = parse_body(good_body())
    body = replace(
        body,
        key_judgements=tuple(
            replace(row, confidence=Confidence.HIGH) for row in body.key_judgements
        ),
    )
    adjusted, view = apply_advocacy(
        body, DevilsAdvocacy("KJ2", "A plausible alternative.", lower_confidence=True)
    )
    assert adjusted.key_judgements[0].confidence is Confidence.HIGH
    assert adjusted.key_judgements[1].confidence is Confidence.MODERATE
    assert view.confidence_before is Confidence.HIGH


def test_unknown_advocacy_target_cannot_change_first_judgement():
    body = parse_body(good_body())
    adjusted, view = apply_advocacy(
        body, DevilsAdvocacy("KJ999", "A plausible alternative.", lower_confidence=True)
    )
    assert adjusted == body and not view.lower_confidence


@pytest.mark.parametrize(
    "value",
    [
        [],
        {},
        {"judgements": "bad"},
        {"judgements": [{"target": "KJ999", "terms": ["x"]}]},
        {"judgements": [{"target": "KJ1", "terms": ["x"]}] * 2},
        {"judgements": [{"target": "KJ1", "terms": [True]}]},
        {"judgements": [{"target": "KJ1", "terms": []}]},
        {"judgements": [{"target": "KJ1", "terms": ["x" * 301]}]},
    ],
)
def test_invalid_query_plans_are_rejected(value):
    with pytest.raises(ValueError):
        parse_plans(value, parse_body(good_body()))


def test_each_missing_review_and_invalid_boolean_is_explicit():
    _, version = document_records()
    payload = reviews()
    payload["judgements"] = [{**payload["judgements"][0], "lower_confidence": "false"}]
    result, _ = parse_reviews(payload, version.body, version.evidence)
    assert [row.status for row in result] == ["invalid", "unavailable"]
    assert all(row.advocacy is None for row in result)
    payload = reviews()
    payload["judgements"][0]["evidence"] = ["E999"]
    assert parse_reviews(payload, version.body, version.evidence)[0][0].status == "invalid"


@pytest.mark.parametrize("failure", [False, True])
async def test_private_collection_reselects_and_reviews_all_final_judgements(
    container, user, failure
):
    _, version = document_records()
    job = production_job(user, container.cipher)
    selected = Selection(version.evidence, 0, 3)
    added = make_event(title="A new contrary observation", source_id="new-source")
    candidate = Selection(
        (
            replace(version.evidence[0], event_id=added.id, content_hash=added.content_hash),
            *version.evidence[1:],
        ),
        0,
        4,
    )
    revised = replace(
        version.body,
        key_judgements=tuple(
            replace(row, statement=row.statement + " Revised.")
            for row in version.body.key_judgements
        ),
    )
    error = Finding("schema", Severity.ERROR, "output", "Replacement draft invalid.")
    redraft = AsyncMock(
        return_value=Draft(body=None if failure else revised, findings=[error] if failure else [])
    )

    def select(terms):
        return candidate

    store = filled_store()
    collection = AsyncMock()
    collection.challenge_many.return_value = (
        ResearchBatch(
            items=(added,),
            attempts=(
                CollectionAttempt("new-source", "New source", CollectionStatus.COMPLETED, 1),
            ),
        ),
        ResearchBatch(
            attempts=(CollectionAttempt("budget", "Budget", CollectionStatus.BUDGET_EXHAUSTED),)
        ),
    )
    gateway = ScriptedGateway(json.dumps(plans()), json.dumps(reviews()))
    totals = Totals(findings=[error] if failure else [])

    async def profile_for(role):
        return job.profile

    result = await run_challenge(
        job,
        Draft(body=version.body),
        selected,
        query=ResearchQuery(job.title, job.now - job.window, job.now),
        store=store,
        collection=collection,
        gateway=gateway,
        cipher=container.cipher,
        profile_for=profile_for,
        totals=totals,
        select=select,
        redraft=redraft,
    )
    assert collection.challenge_many.await_count == 1
    assert len(collection.challenge_many.await_args.args[0]) == 2
    assert result.challenge.redrafted is not failure
    assert result.selection is (selected if failure else candidate)
    assert len(result.challenge.searches) == len(result.challenge.reviews) == 2
    assert result.challenge.searches[1].attempts[0].status is CollectionStatus.BUDGET_EXHAUSTED
    assert result.challenge.searches[1].status == "budget_exhausted"
    assert all(row.status == "completed" for row in result.challenge.reviews)
    assert result.challenge.reviews[0].statement.endswith("Revised.") is not failure
    assert result.challenge.searches[0].statement == version.body.key_judgements[0].statement
    assert all(row.confidence is Confidence.LOW for row in result.body.key_judgements)
    assert [request.schema_name for request in gateway.requests] == [
        "challenge_plan",
        "challenge_reviews",
    ]
    assert not totals.usage[0].purpose.endswith("advocacy")
    assert all(row.severity is not Severity.ERROR for row in totals.findings)


@pytest.mark.parametrize(
    "mode", ["missing_profile", "missing_plan", "bad_collection", "no_items", "private", "busy"]
)
async def test_unavailable_challenge_does_not_claim_confirmation(container, user, mode):
    _, version = document_records()
    job = production_job(user, container.cipher)
    selected = Selection(version.evidence, 0, 3)
    gateway = ScriptedGateway(
        json.dumps({"judgements": []} if mode == "missing_plan" else plans()),
        json.dumps({"judgements": []}),
    )
    collection = AsyncMock()
    if mode == "busy":
        collection.challenge_many.side_effect = RateLimited(5)
    collection.challenge_many.return_value = (
        () if mode == "bad_collection" else (ResearchBatch(), ResearchBatch())
    )

    async def profile_for(role):
        return None if mode == "missing_profile" else job.profile

    redraft = AsyncMock()
    focus = ResearchFocus.DOCUMENT if mode == "private" else ResearchFocus.GENERAL
    result = await run_challenge(
        job,
        Draft(body=version.body),
        selected,
        query=ResearchQuery(job.title, job.now - job.window, job.now, focus=focus),
        store=filled_store(),
        collection=collection,
        gateway=gateway,
        cipher=container.cipher,
        profile_for=profile_for,
        totals=Totals(),
        select=lambda terms: selected,
        redraft=redraft,
    )
    assert not result.challenge.redrafted and result.body == version.body
    assert len(result.challenge.reviews) == 2
    assert all(row.status == "unavailable" for row in result.challenge.reviews)
    redraft.assert_not_awaited()
    assert any("do not confirm" in note for note in result.challenge.limitations)
    if mode == "private":
        collection.challenge_many.assert_not_awaited()
        assert "disabled for private" in result.challenge.searches[0].explanation
    if mode == "busy":
        assert result.challenge.searches[0].status == "unavailable"
        assert "busy" in result.challenge.searches[0].explanation


async def test_model_failure_is_safe_and_no_retry(container, user):
    job = production_job(user, container.cipher)
    gateway = AsyncMock()
    gateway.complete.side_effect = TimeoutError("contains sensitive query")
    result = await challenge_call(gateway, job.profile, "key", parse_body(good_body()))
    assert not result.succeeded and gateway.complete.await_count == 1
    assert "sensitive" not in result.findings[0].message
    gateway.complete.side_effect = None
    gateway.complete.return_value = LlmResult("{", "model", 1, 2, 3)
    result = await challenge_call(gateway, job.profile, "key", parse_body(good_body()))
    assert not result.succeeded and result.prompt_tokens == 2
