"""Folded source provenance remains gated across durable admission and replay."""

from dataclasses import replace
from datetime import timedelta

import pytest

from ase.application.reports.challenge_expansion_checkpoint import (
    ExpansionPacket,
    ExpansionPlan,
    packet_to_dict,
    plan_to_dict,
)
from ase.application.reports.challenge_expansion_partial import KEY, PartialResult, encode_partial
from ase.container.report_job_cache import AttemptCache, attempt_cache
from ase.container.report_job_gate import ReportJobSourceDisabled, check_sources
from ase.domain.evidence import CorroborationMember
from ase.domain.report_records import evidence_to_list
from ase.domain.research import CollectionAttempt, CollectionStatus, ResearchQuery
from ase.domain.research_records import ResearchReceipt
from feeds_helpers import NOW
from report_documents_helpers import document_records
from report_job_snapshot_helpers import fixture_evidence
from test_report_job_gate import checkpoint, host, saved


def folded(*source_ids):
    return replace(
        fixture_evidence(),
        source_id="allowed-primary",
        corroboration=tuple(
            CorroborationMember(f"copy-{index}", source_id, source_id, source_id, "Saved report")
            for index, source_id in enumerate(source_ids)
        ),
    )


def retained(placement, evidence):
    stored = saved()
    baseline = None
    if placement == "frozen":
        stored = saved(frozen=(evidence,))
    elif placement == "collection":
        stored = saved(collection=checkpoint(evidence=(evidence,)))
    elif placement == "expansion":
        query = ResearchQuery("What changed?", NOW - timedelta(days=1), NOW)
        stored.payload["challenge_expansion_packet"] = packet_to_dict(
            ExpansionPacket(
                "a" * 64,
                "b" * 64,
                (evidence,),
                ResearchReceipt.build(query, (), 1),
                "attempted",
                "Saved source result",
            )
        )
    elif placement == "partial":
        plan = ExpansionPlan("a" * 64, "b" * 64, "KJ1", ("contrary",), ("public",), "ready")
        stored.payload["challenge_expansion_plan"] = plan_to_dict(plan)
        stored.payload[KEY] = encode_partial(
            (
                PartialResult(
                    "challenge:" + "c" * 64,
                    (evidence,),
                    CollectionAttempt("public", "Public", CollectionStatus.COMPLETED, 1, "Saved"),
                ),
            ),
            plan.fingerprint,
        )
    else:
        _, baseline = document_records()
        baseline = replace(baseline, evidence=(evidence,))
    return stored, baseline


@pytest.mark.parametrize("placement", ["frozen", "collection", "expansion", "partial", "baseline"])
async def test_denied_folded_source_blocks_each_retained_boundary(placement):
    stored, baseline = retained(placement, folded("denied-member"))
    container = host("denied-member")
    with pytest.raises(ReportJobSourceDisabled):
        await check_sources(container, stored, baseline)
    assert set(container.source_admission.enabled_many.await_args.args[0]) == {
        "allowed-primary",
        "denied-member",
    }


@pytest.mark.parametrize("placement", ["frozen", "collection", "expansion", "partial", "baseline"])
async def test_permitted_folded_sources_preserve_retained_work(placement):
    stored, baseline = retained(placement, folded("allowed-member", "allowed-primary"))
    container = host()
    await check_sources(container, stored, baseline)
    queried = container.source_admission.enabled_many.await_args.args[0]
    assert set(queried) == {"allowed-primary", "allowed-member"} and len(queried) == 2


async def test_cached_provenance_rechecks_folded_sources_against_current_admission():
    stored = saved(frozen=(folded("member"),))
    container = host()
    token = attempt_cache.set(AttemptCache())
    try:
        await check_sources(container, stored)
        container.source_admission.enabled_many.side_effect = lambda ids: {
            key: key != "member" for key in ids
        }
        with pytest.raises(ReportJobSourceDisabled):
            await check_sources(container, stored)
        assert container.source_admission.enabled_many.await_count == 2
        assert "member" in container.source_admission.enabled_many.await_args.args[0]
    finally:
        attempt_cache.reset(token)


async def test_cached_provenance_invalidates_when_only_folded_payload_changes():
    stored = saved(frozen=(folded(),))
    container = host("new-member")
    token = attempt_cache.set(AttemptCache())
    try:
        await check_sources(container, stored)
        stored.payload["input"]["evidence"] = evidence_to_list((folded("new-member"),))
        with pytest.raises(ReportJobSourceDisabled):
            await check_sources(container, stored)
        assert "new-member" in container.source_admission.enabled_many.await_args.args[0]
    finally:
        attempt_cache.reset(token)


async def test_fresh_subscription_baseline_is_checked_even_when_job_payload_is_cached():
    stored, baseline = retained("baseline", folded("new-member"))
    container = host("new-member")
    token = attempt_cache.set(AttemptCache())
    try:
        await check_sources(container, stored)
        with pytest.raises(ReportJobSourceDisabled):
            await check_sources(container, stored, baseline)
        assert "new-member" in container.source_admission.enabled_many.await_args.args[0]
    finally:
        attempt_cache.reset(token)
