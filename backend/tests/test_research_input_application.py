"""Upload admission, fresh access decisions and extraction cancellation cleanup."""

import asyncio
from dataclasses import replace
from datetime import timedelta

import pytest

from ase.adapters.research_imports.models import ImportRejected
from ase.adapters.research_inputs.importer import DocumentResearchImporter
from ase.application.ports.research_inputs import INPUT_TTL_SECONDS, MAX_INPUT_BYTES
from ase.application.research.inputs import INPUT_ATTEMPTS_PER_WINDOW
from ase.domain.errors import InvalidRequest, NotFound, RateLimited, Unauthenticated
from research_input_helpers import NOW, Harness


async def test_success_retains_only_extracted_private_evidence() -> None:
    harness = Harness()
    receipt = await harness.service.execute(harness.actor, "notes.txt", b"Private upload.")
    stored = harness.store.read(harness.actor, receipt.id)
    assert stored.events[0].summary == "Private upload."
    assert receipt.event_count == 1 and receipt.extracted_characters == 15
    assert receipt.expires_at - receipt.imported_at == timedelta(seconds=INPUT_TTL_SECONDS)
    assert harness.uow.rollbacks == 3 and not harness.identity.locked


@pytest.mark.parametrize("change", [{"is_active": False}, {"security_version": 1}])
async def test_identity_changes_during_extraction_prevent_retention(
    change: dict[str, object],
) -> None:
    harness = Harness()
    harness.extractor.change = change
    with pytest.raises(Unauthenticated):
        await harness.service.execute(harness.actor, "notes.txt", b"Private upload.")
    assert harness.extractor.calls == 1
    assert not harness.store._reservations and not harness.store._ready
    assert not harness.identity.locked


async def test_stale_identity_is_rejected_before_body_admission() -> None:
    harness = Harness()
    harness.identity.current = replace(harness.actor, is_active=False)
    with pytest.raises(Unauthenticated):
        await harness.service.reserve(harness.actor, "notes.txt")
    assert not harness.store._reservations and harness.extractor.calls == 0


@pytest.mark.parametrize("error", [InvalidRequest(), asyncio.CancelledError()])
async def test_parser_failure_and_cancellation_release_pending_slot(error: BaseException) -> None:
    harness = Harness()
    harness.extractor.error = error
    with pytest.raises(type(error)):
        await harness.service.execute(harness.actor, "notes.txt", b"Private upload.")
    assert not harness.store._reservations and not harness.store._ready


async def test_repeated_failures_use_shared_per_user_rate_budget() -> None:
    harness = Harness()
    harness.extractor.error = InvalidRequest()
    for _ in range(INPUT_ATTEMPTS_PER_WINDOW):
        with pytest.raises(InvalidRequest):
            await harness.service.execute(harness.actor, "notes.txt", b"bad")
    with pytest.raises(RateLimited) as error:
        await harness.service.execute(harness.actor, "notes.txt", b"bad")
    assert error.value.retry_after == INPUT_TTL_SECONDS
    assert harness.extractor.calls == INPUT_ATTEMPTS_PER_WINDOW


@pytest.mark.parametrize("filename", ["../notes.txt", "notes\n.txt", "C:notes.txt", "   "])
async def test_filename_must_be_a_plain_bounded_display_label(filename: str) -> None:
    harness = Harness()
    with pytest.raises(InvalidRequest):
        await harness.service.reserve(harness.actor, filename)
    assert not harness.store._reservations and harness.extractor.calls == 0


@pytest.mark.parametrize("data", [b"", b"x" * (MAX_INPUT_BYTES + 1)], ids=["empty", "oversized"])
async def test_empty_and_oversized_input_never_reaches_parser(data: bytes) -> None:
    harness = Harness()
    with pytest.raises(InvalidRequest):
        await harness.service.execute(harness.actor, "notes.txt", data)
    assert harness.extractor.calls == 0 and not harness.store._reservations


async def test_expiry_while_streaming_prevents_parser_admission() -> None:
    harness = Harness()
    pending = await harness.service.reserve(harness.actor, "notes.txt")
    harness.clock.advance(timedelta(seconds=INPUT_TTL_SECONDS))
    with pytest.raises(NotFound):
        await harness.service.execute_reserved(harness.actor, pending, b"text")
    assert harness.extractor.calls == 0


async def test_adapter_bridge_translates_runner_rejection_without_parser_details() -> None:
    class RejectedRunner:
        async def run(self, data: bytes, filename: str) -> None:
            raise ImportRejected("The document is malformed or uses an unsupported feature.")

    bridge = DocumentResearchImporter(RejectedRunner())
    with pytest.raises(InvalidRequest, match="malformed"):
        await bridge.extract(b"bad", "notes.pdf", NOW)
