"""Acquire only admitted originals, charge attempts and recheck access before release."""

import asyncio
from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest

from ase.application.research.original_acquisition import OriginalAcquisitionBudget
from ase.domain.errors import NotFound
from ase.domain.research import ResearchMode
from original_acquisition_support import Harness, access, extraction, policy, response


async def test_acquisition_preserves_exact_original_and_separates_discovery_metadata():
    harness = Harness()
    result = await harness.acquire()
    assert result.receipt.status == "acquired"
    assert result.original_bytes == harness.response.body
    assert result.document.passages[0].text == "Exact original passage."
    assert "Generated discovery" not in result.document.passages[0].text
    assert result.document.published_at is None
    assert result.document.original_language == "und"
    assert result.document.requirement_ids == ("q1",)
    assert result.receipt.documents_attempted == result.receipt.source_operations == 1
    assert result.receipt.transport_requests == 1
    assert harness.budget.transport_requests_remaining == 11
    assert harness.requests[0].policy is harness.policy
    assert harness.requests[0].accept_encoding == "identity"
    assert harness.admission.depth == 0


@pytest.mark.parametrize(
    "changes",
    [
        {"terms": "unknown"},
        {"terms": "denied"},
        {"robots": "unknown"},
        {"robots": "denied"},
        {"permitted_use": ""},
        {"source_id": "different"},
    ],
)
async def test_unreviewed_policy_never_dispatches_or_spends(changes):
    harness = Harness()
    harness.policy = policy(**changes)
    result = await harness.acquire()
    assert result.receipt.reason == "policy_or_destination_not_permitted"
    assert result.receipt.source_operations == result.receipt.transport_requests == 0
    assert not harness.requests and harness.budget.documents_attempted == 0
    assert result.document is None and result.original_bytes == b""


async def test_disabled_source_missing_transport_and_allowance_stop_before_dispatch():
    harness = Harness()
    harness.admission.allowed = False
    assert (await harness.acquire()).receipt.reason == "source_disabled"
    harness.admission.allowed = True
    harness.service.fetch = None
    assert (await harness.acquire()).receipt.reason == "guarded_transport_unavailable"
    harness.service.fetch = harness.fetch
    harness.budget.source_operations_remaining = 0
    assert (await harness.acquire()).receipt.reason == "insufficient_remaining_allowance"
    assert harness.budget.documents_attempted == 0 and not harness.requests


@pytest.mark.parametrize(
    "bad_response",
    [
        response(hops=()),
        response(content_encoding="gzip"),
        response(media_type="text/html"),
    ],
)
async def test_failed_safety_receipt_keeps_headline_only_and_uncertain_reservation(bad_response):
    harness = Harness()
    harness.response = bad_response
    result = await harness.acquire()
    assert result.receipt.status == "headline_only"
    assert result.receipt.transport_requests is None
    assert result.receipt.transport_requests_reserved == 3
    assert result.document is None and not result.original_bytes
    assert harness.parser.calls == 0
    assert harness.budget.documents_attempted == 1
    assert harness.budget.source_operations_remaining == 5
    assert harness.budget.transport_requests_remaining == 9
    assert harness.catalogue.candidates[harness.candidate.id].headline


async def test_parser_provenance_failure_returns_no_original_bytes():
    harness = Harness()

    async def mismatched(body, filename, captured_at):
        return extraction(body, "wrong-file.txt")

    harness.parser.extract = mismatched
    result = await harness.acquire()
    assert result.receipt.reason == "parser_provenance_mismatch"
    assert result.receipt.transport_requests == 1
    assert result.document is None and not result.original_bytes


async def test_foreign_correction_link_is_rejected_before_dispatch_or_expenditure():
    first = Harness()
    previous = (await first.acquire()).document
    other = Harness()
    with pytest.raises(NotFound):
        await other.acquire(previous=previous)
    assert not other.requests and other.budget.documents_attempted == 0


async def test_correction_reuses_current_scope_and_preserves_previous_hash():
    harness = Harness()
    first = (await harness.acquire()).document
    harness.response = response(b"corrected original")
    result = await harness.acquire(previous=first)
    assert result.document.previous_sha256 == first.sha256
    assert result.receipt.status == "acquired"


@pytest.mark.parametrize("stage", ["fetch", "parser"])
async def test_exceptions_never_echo_untrusted_document_or_credential_text(stage):
    harness = Harness()

    async def fail(*args):
        raise RuntimeError("private passage and secret credential")

    if stage == "fetch":
        harness.service.fetch = fail
    else:
        harness.parser.extract = fail
    result = await harness.acquire()
    assert result.receipt.reason == f"{stage}_rejected"
    assert "private" not in repr(result) and "credential" not in repr(result)
    assert result.receipt.transport_requests == (None if stage == "fetch" else 1)


@pytest.mark.parametrize("stage", ["fetch", "parser"])
async def test_timeout_cancels_worker_and_retains_attempt_charge(stage):
    harness = Harness()
    harness.policy = policy(timeout_seconds=0.02)
    stopped = asyncio.Event()

    async def block(*args):
        try:
            await asyncio.Event().wait()
        finally:
            stopped.set()

    if stage == "fetch":
        harness.service.fetch = block
    else:
        harness.parser.extract = block
    result = await harness.acquire()
    assert result.receipt.reason == f"{stage}_timeout"
    assert stopped.is_set() and harness.budget.documents_attempted == 1
    assert result.document is None and not result.original_bytes


async def test_caller_cancellation_propagates_and_does_not_refund_uncertain_transport():
    harness = Harness()
    started, stopped = asyncio.Event(), asyncio.Event()

    async def block(request):
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            stopped.set()

    harness.service.fetch = block
    task = asyncio.create_task(harness.acquire())
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert stopped.is_set()
    assert harness.budget.transport_requests_remaining == 9
    assert harness.admission.depth == 0


@pytest.mark.parametrize("change", ["source", "access", "policy"])
async def test_current_source_access_and_policy_rechecked_after_parsing(change):
    harness = Harness()

    async def change_state(body, filename, captured_at):
        assert harness.admission.depth == 0
        if change == "source":
            harness.admission.allowed = False
        elif change == "access":
            harness.access = access(uuid4())
        else:
            harness.clock.value = harness.policy.valid_until + timedelta(seconds=1)
        return extraction(body, filename)

    harness.parser.extract = change_state
    if change == "access":
        with pytest.raises(NotFound):
            await harness.acquire()
    else:
        result = await harness.acquire()
        assert result.receipt.reason == (
            "source_disabled_after_acquisition"
            if change == "source"
            else "policy_expired_after_acquisition"
        )
        assert not result.original_bytes and result.document is None
    assert harness.budget.documents_attempted == 1


@pytest.mark.parametrize(
    ("mode", "ceiling"),
    [
        (ResearchMode.QUICK, 2),
        (ResearchMode.DETAILED, 6),
        (ResearchMode.ADVANCED, 10),
    ],
)
def test_follow_through_ceiling_counts_every_attempt(mode, ceiling):
    budget = OriginalAcquisitionBudget(
        mode,
        remaining_source_operations=32,
        remaining_transport_requests=128,
        remaining_seconds=240,
        monotonic=lambda: 0,
    )
    for _ in range(ceiling):
        assert budget.reserve(policy()) is not None
    assert budget.reserve(policy()) is None
    assert budget.documents_attempted == ceiling


@pytest.mark.parametrize(
    "limits",
    [
        {"remaining_source_operations": 0},
        {"remaining_transport_requests": 2},
        {"remaining_seconds": 19},
        {"documents_attempted": 2},
    ],
)
def test_reservation_cannot_overrun_remaining_job_allowance(limits):
    values = {
        "remaining_source_operations": 6,
        "remaining_transport_requests": 12,
        "remaining_seconds": 45,
        "monotonic": lambda: 0,
    }
    budget = OriginalAcquisitionBudget(ResearchMode.QUICK, **(values | limits))
    assert budget.reserve(policy()) is None


@pytest.mark.parametrize(
    "limits",
    [
        {"remaining_source_operations": 33},
        {"remaining_transport_requests": -1},
        {"remaining_seconds": 241},
        {"documents_attempted": 3},
    ],
)
def test_invalid_job_allowance_is_rejected(limits):
    values = {
        "remaining_source_operations": 6,
        "remaining_transport_requests": 12,
        "remaining_seconds": 45,
    }
    with pytest.raises(ValueError):
        OriginalAcquisitionBudget(ResearchMode.QUICK, **(values | limits))


def test_transport_refund_requires_owned_reservation_and_happens_exactly_once():
    harness = Harness()
    reservation = harness.budget.reserve(harness.policy)
    with pytest.raises(ValueError):
        harness.budget.settle_known(replace(reservation, id=uuid4()), 1)
    with pytest.raises(ValueError):
        harness.budget.settle_known(reservation, 4)
    harness.budget.settle_known(reservation, 1)
    with pytest.raises(ValueError):
        harness.budget.settle_known(reservation, 1)
    assert harness.budget.transport_requests_remaining == 11
