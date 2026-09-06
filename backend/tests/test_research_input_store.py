"""Private extraction ownership, expiry, immutable snapshots and bounded capacity."""

from dataclasses import FrozenInstanceError, replace
from datetime import timedelta
from uuid import uuid4

import pytest

from ase.adapters.research_inputs import memory
from ase.application.ports.research_inputs import INPUT_TTL_SECONDS
from ase.domain.errors import InvalidRequest, NotFound, RateLimited
from ase.domain.users import Role
from research_input_helpers import Harness, actor, extracted


def test_store_is_private_even_to_admin_and_bound_to_identity_generation() -> None:
    harness = Harness()
    reservation = harness.store.reserve(harness.actor, "notes.txt")
    with pytest.raises(NotFound):
        harness.store.read(harness.actor, reservation.id)
    stored = harness.store.put(reservation, extracted())
    assert harness.store.read(harness.actor, reservation.id) is stored
    for other in (
        actor(),
        replace(actor(), role=Role.ADMIN),
        replace(harness.actor, security_version=1),
        replace(harness.actor, is_active=False),
    ):
        with pytest.raises(NotFound):
            harness.store.read(other, reservation.id)
    with pytest.raises(NotFound):
        harness.store.read(harness.actor, uuid4())
    harness.store.release(reservation)
    assert harness.store.read(harness.actor, reservation.id) is stored
    harness.clock.advance(timedelta(seconds=INPUT_TTL_SECONDS))
    with pytest.raises(NotFound):
        harness.store.read(harness.actor, reservation.id)
    assert not harness.store._reservations and not harness.store._sizes


def test_snapshot_does_not_retain_mutable_parser_attributes() -> None:
    harness = Harness()
    content = extracted()
    metadata = {"original": "kept"}
    content = replace(content, events=(replace(content.events[0], attributes=metadata),))
    reservation = harness.store.reserve(harness.actor, content.filename)
    stored = harness.store.put(reservation, content)
    metadata["original"] = "changed"
    assert stored.events[0].attributes["original"] == "kept"
    with pytest.raises(TypeError):
        stored.events[0].attributes["original"] = "changed"
    with pytest.raises(FrozenInstanceError):
        stored.receipt.filename = "changed"
    assert not hasattr(stored, "data")
    assert stored.receipt.preview == "Original factual claim."
    assert stored.events[0].grade == "F6"


def test_pending_and_complete_inputs_share_user_and_global_slot_budgets() -> None:
    harness = Harness()
    first = harness.store.reserve(harness.actor, "notes.txt")
    second = harness.store.reserve(harness.actor, "notes.txt")
    harness.store.put(first, extracted())
    with pytest.raises(RateLimited):
        harness.store.reserve(harness.actor, "notes.txt")
    for _ in range(6):
        harness.store.reserve(actor(), "notes.txt")
    with pytest.raises(RateLimited):
        harness.store.reserve(actor(), "notes.txt")
    harness.store.release(second)
    harness.store.reserve(actor(), "notes.txt")
    assert harness.store.read(harness.actor, first.id)


def test_expired_or_reused_reservation_cannot_store_or_start_extraction() -> None:
    harness = Harness()
    pending = harness.store.reserve(harness.actor, "notes.txt")
    harness.clock.advance(timedelta(seconds=INPUT_TTL_SECONDS))
    with pytest.raises(NotFound):
        harness.store.require_pending(pending)
    with pytest.raises(NotFound):
        harness.store.put(pending, extracted())
    new = harness.store.reserve(harness.actor, "notes.txt")
    harness.store.put(new, extracted())
    with pytest.raises(NotFound):
        harness.store.put(new, extracted())


@pytest.mark.parametrize("kind", ["empty", "hash", "passage", "total", "metadata", "filename"])
def test_extracted_limits_are_enforced_again_at_retention_boundary(kind: str) -> None:
    harness = Harness()
    content = extracted()
    if kind == "empty":
        content = replace(content, events=())
    elif kind == "hash":
        content = replace(content, sha256="bad")
    elif kind == "passage":
        content = replace(content, events=(replace(content.events[0], summary="x" * 1801),))
    elif kind == "total":
        content = replace(content, events=(replace(content.events[0], summary="x" * 1800),) * 112)
    elif kind == "metadata":
        content = replace(content, events=(replace(content.events[0], attributes={"x": {}}),))
    else:
        content = replace(content, filename="different.txt")
    pending = harness.store.reserve(harness.actor, "notes.txt")
    with pytest.raises(InvalidRequest):
        harness.store.put(pending, content)
    with pytest.raises(NotFound):
        harness.store.read(harness.actor, pending.id)


def test_global_estimated_memory_bound_rejects_without_evicting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = Harness()
    content = extracted()
    _, size = memory._freeze_and_measure(content)
    monkeypatch.setattr(memory, "MAX_ESTIMATED_BYTES", size)
    first = harness.store.reserve(harness.actor, "notes.txt")
    harness.store.put(first, content)
    second = harness.store.reserve(actor(), "notes.txt")
    with pytest.raises(RateLimited):
        harness.store.put(second, content)
    assert harness.store.read(harness.actor, first.id).receipt.sha256 == content.sha256
