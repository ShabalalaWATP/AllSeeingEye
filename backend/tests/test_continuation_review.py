"""Continuation decisions remain bounded, cited and subordinate to operator tasks."""

import json
from dataclasses import asdict, replace

import pytest

from ase.application.ports.research import ContinuationProposal
from ase.application.research import replanning
from ase.application.research.budget import CollectionRunBudget
from ase.application.research.continuation_review import (
    evidence_context,
    parse_review,
    validate_proposal,
)
from ase.application.research.pacing import RequestPacer
from ase.application.research.planning import build_plan
from ase.application.research.service import ResearchCollectionService
from ase.domain.research import CollectionAttempt, CollectionStatus, ResearchBatch
from ase.domain.research_continuation import ContinuationTrace, EvidenceExcerpt
from ase.domain.research_records import ResearchReceipt, research_from_dict, research_to_dict
from ase.domain.research_tasks import PlannedQueryTask
from test_research_collection import QUERY, Provider, event


def item(key="one"):
    return replace(
        event(key),
        title="The facility opened on Monday according to the notice.",
        content_hash="a" * 64,
    )


def trace(batch, decision="sufficient", basis="question_addressed"):
    return ContinuationTrace(
        decision,
        decision,
        basis,
        "The supplied notice addresses opening time.",
        tuple(
            EvidenceExcerpt(row.id, row.source_id, row.content_hash, "title", row.title)
            for row in batch.items[:2]
        ),
        (),
        "fixture",
        len(evidence_context(batch)),
        len(batch.items),
    )


def payload(batch):
    row = trace(batch)
    return {
        "decision": row.decision,
        "basis": row.basis,
        "rationale": row.rationale,
        "citations": [asdict(c) for c in row.citations],
        "gaps": [],
        "query": None,
    }


@pytest.mark.parametrize(
    "mutation", ["hash", "source", "quote", "field", "extra", "duplicate", "control"]
)
def test_invalid_citations_are_rejected(mutation):
    batch = ResearchBatch(items=(item(),))
    value = payload(batch)
    citation = value["citations"][0]
    if mutation == "duplicate":
        value["citations"].append(citation.copy())
    else:
        key = {
            "hash": "content_hash",
            "source": "source_id",
            "quote": "quote",
            "field": "field",
            "extra": "instructions",
            "control": "quote",
        }[mutation]
        citation[key] = "bad\nquote" if mutation == "control" else "invented"
    with pytest.raises((ValueError, TypeError)):
        parse_review(json.dumps(value), batch, "fixture")


def test_context_is_complete_json_byte_bounded_and_excludes_attributes_urls():
    batch = ResearchBatch(
        items=tuple(
            replace(
                item(str(n)),
                summary="中" * 2000,
                url="https://private.invalid",
                attributes={"instruction": "stop"},
            )
            for n in range(30)
        )
    )
    context = evidence_context(batch)
    assert 0 < len(context) < 20
    assert len(json.dumps(context, ensure_ascii=False).encode()) <= 24 * 1024
    assert all(row["summary"] == "中" * 2000 for row in context)
    assert "private.invalid" not in str(context) and "instruction" not in str(context)
    proposal = validate_proposal(ContinuationProposal(None, trace(batch)), QUERY, batch)
    assert proposal.trace.decision == "continue"


@pytest.mark.parametrize("status", list(CollectionStatus))
def test_operator_tasks_must_all_complete_before_stopping(status):
    query = replace(
        QUERY, planned_tasks=(PlannedQueryTask("challenge", "test", "challenge", ("disprove",)),)
    )
    batch = ResearchBatch(
        items=(item(),),
        attempts=(
            CollectionAttempt(
                "test", "Test", status, task_id="operator:challenge", purpose="challenge"
            ),
        ),
    )
    result = validate_proposal(ContinuationProposal(None, trace(batch)), query, batch)
    assert (result.trace.decision == "sufficient") == (
        status in {CollectionStatus.EMPTY, CollectionStatus.COMPLETED}
    )


@pytest.mark.parametrize("change", ["gap", "conflict", "short", "count"])
def test_inadequate_stop_is_overridden(change):
    batch = ResearchBatch(items=(item(),))
    review = trace(batch)
    if change == "gap":
        review = replace(review, gaps=("Date unclear",))
    elif change == "conflict":
        review = replace(review, basis="potential_conflict")
    elif change == "short":
        review = replace(review, citations=(replace(review.citations[0], quote="The"),))
    else:
        review = replace(review, context_count=0)
    assert (
        validate_proposal(ContinuationProposal(None, review), QUERY, batch).trace.decision
        == "continue"
    )


@pytest.mark.parametrize("decision", ["sufficient", "replan", "continue", "legacy"])
async def test_real_collection_actions_and_saved_trace(decision, monkeypatch):
    async def wait(self):
        pass

    monkeypatch.setattr(RequestPacer, "wait", wait)
    providers = [Provider(str(n), batch=ResearchBatch(items=(item(str(n)),))) for n in range(6)]
    calls = []

    async def callback(query, first, remaining):
        calls.append(remaining)
        if decision == "legacy":
            return replace(query, terms=("revised",))
        review = trace(
            first, decision, "potential_conflict" if decision == "replan" else "question_addressed"
        )
        return ContinuationProposal(
            replace(query, terms=("revised",)) if decision == "replan" else None, review
        )

    result = await ResearchCollectionService(lambda _: providers).collect(QUERY, replan=callback)
    assert len(calls) == 1 and result.plan.model_calls == 1
    assert result.plan.replans == int(decision == "replan")
    assert sum(row.called for row in providers) == (3 if decision == "sufficient" else 6)
    if decision == "sufficient":
        assert all(row.status is CollectionStatus.NOT_COLLECTED for row in result.attempts[3:])
    receipt = ResearchReceipt.build(
        QUERY, result.attempts, len(result.items), result.plan, result.passes
    )
    assert research_from_dict(json.loads(json.dumps(research_to_dict(receipt)))) == receipt


def test_legacy_plan_has_no_new_null_field():

    plan = build_plan(QUERY, [], requests=6, seconds=20, items=20)
    receipt = ResearchReceipt.build(QUERY, (), 0, plan)
    encoded = research_to_dict(receipt)
    assert "continuation" not in encoded["plan"]
    assert research_to_dict(research_from_dict(encoded)) == encoded


@pytest.mark.parametrize("expire_before_pass", [True, False])
async def test_deadline_prevents_unperformed_replan_claim(expire_before_pass, monkeypatch):

    now = [0.0]
    reviewed = [False]
    budget = CollectionRunBudget(
        replanning.CollectionBudget.for_mode(QUERY.mode), clock=lambda: now[0]
    )
    monkeypatch.setattr(replanning, "CollectionRunBudget", lambda limits: budget)

    admit = budget.admit

    def expire_at_admission():
        if not expire_before_pass and reviewed[0]:
            now[0] = 100
        return admit()

    monkeypatch.setattr(budget, "admit", expire_at_admission)

    async def wait(self):
        pass

    monkeypatch.setattr(RequestPacer, "wait", wait)
    providers = [Provider(str(n), batch=ResearchBatch(items=(item(str(n)),))) for n in range(6)]

    async def callback(query, first, remaining):
        reviewed[0] = True
        if expire_before_pass:
            now[0] = 100
        return ContinuationProposal(
            replace(query, terms=("revised",)), trace(first, "replan", "potential_conflict")
        )

    result = await ResearchCollectionService(lambda _: providers).collect(QUERY, replan=callback)
    assert sum(row.called for row in providers) == 3
    assert result.plan.replans == 0 and result.plan.model_calls == 1
    assert result.plan.continuation.decision == "continue"
    assert result.plan.continuation.requested_decision == "replan"


def test_describe_retains_denied_stop_gaps_and_override():
    batch = ResearchBatch(items=(item(),))
    review = replace(
        trace(batch),
        decision="continue",
        gaps=("Missing date",),
        override_reason="Operator tasks remain incomplete",
    )
    plan = replace(build_plan(QUERY, [], requests=6, seconds=20, items=20), continuation=review)
    description = ResearchReceipt.build(QUERY, (), 1, plan).describe()
    assert "Missing date" in description and "Operator tasks remain incomplete" in description
