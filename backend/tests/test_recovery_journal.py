"""External evidence fails closed on tampering, gaps, uncertainty and unsafe paths."""

import json
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError

from ase.adapters.security import recovery_files, recovery_journal
from ase.adapters.security.recovery_journal import FileRecoveryJournal
from ase.adapters.security.recovery_schema import CopyReview, Restriction
from ase.domain.errors import Conflict
from ase.domain.private_removal import RemovalRequest, RemovalScope, ReviewDecision, ReviewPurpose
from recovery_helpers import journal as journal  # noqa: PLC0414

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def review(journal):
    return journal.begin_review(
        uuid4(),
        uuid4(),
        ReviewDecision.REMOVE,
        ReviewPurpose.RIGHTS_REQUEST,
        1,
        NOW,
        NOW + timedelta(days=90),
    )


def test_encrypted_records_distinguish_permissions_mutations_and_instructions(journal):
    permission = review(journal)
    journal.complete(permission)
    owner = uuid4()
    removal = journal.begin_removal(uuid4(), RemovalRequest(owner, RemovalScope.ACCOUNT), NOW)
    journal.complete(removal)
    journal.record(
        uuid4(),
        Restriction(
            owner=owner,
            restriction="objection",
            purpose=ReviewPurpose.RIGHTS_REQUEST,
            due=NOW + timedelta(days=90),
        ),
        NOW,
    )
    journal.record(
        uuid4(),
        CopyReview(
            reference=uuid4(),
            category="mailbox",
            purpose=ReviewPurpose.QUARTERLY,
            due=NOW + timedelta(days=90),
            hold=True,
        ),
        NOW,
    )
    result = journal.inspect()
    events = result["events"]
    assert [e["action"]["kind"] for e in events] == [
        "review",
        "removal",
        "restriction",
        "copy_review",
    ]
    assert [e["status"] for e in events] == ["committed", "committed", "recorded", "recorded"]
    assert result["activation_authorised"] is False and result["unresolved_intents"] == []
    assert len(result["overdue_record_ids"]) == 3
    assert str(owner).encode() not in journal.path.read_bytes()
    assert b"objection" not in journal.path.read_bytes()


def test_pending_intents_block_new_mutations_and_need_bound_evidence(journal):
    event = review(journal)
    with pytest.raises(Conflict, match="unresolved"):
        review(journal)
    before = journal.inspect()
    with pytest.raises(Conflict, match="changed"):
        journal.resolve(event, False, uuid4(), "a" * 64, "0" * 64)
    with pytest.raises(ValidationError):
        journal.resolve(event, False, uuid4(), "not a digest", before["head_sha256"])
    assert journal.inspect() == before
    journal.resolve(event, False, uuid4(), "a" * 64, before["head_sha256"])
    after = journal.inspect()
    assert after["events"][0]["status"] == "not_applied"
    assert after["events"][0]["resolution"]["evidence_sha256"] == "a" * 64
    assert after["head_sha256"] != before["head_sha256"]
    with pytest.raises(Conflict, match="unresolved intent"):
        journal.complete(event)
    with pytest.raises(Conflict, match="unresolved intent"):
        journal.complete(uuid4())


def test_committed_resolution_does_not_create_a_new_event(journal):
    event = review(journal)
    journal.resolve(event, True, uuid4(), "b" * 64, journal.inspect()["head_sha256"])
    events = journal.inspect()["events"]
    assert len(events) == 1 and events[0]["status"] == "committed"


@pytest.mark.parametrize(
    "failure", ["missing", "corrupt", "wrong_key", "malformed", "sequence", "unknown"]
)
def test_existing_history_is_never_silently_reset(journal, failure):
    review(journal)
    cipher = Fernet(journal.key.read_bytes())
    if failure == "missing":
        journal.path.unlink()
    elif failure == "corrupt":
        journal.path.write_bytes(b"broken ciphertext")
    elif failure == "wrong_key":
        journal.key.write_bytes(Fernet.generate_key())
    else:
        data = json.loads(cipher.decrypt(journal.path.read_bytes()))
        if failure == "malformed":
            data = {"unknown": True}
        elif failure == "sequence":
            data["entries"][0]["sequence"] = 3
        else:
            data["entries"][0]["action"]["kind"] = "unknown"
        journal.path.write_bytes(cipher.encrypt(json.dumps(data).encode()))
    with pytest.raises(Conflict, match="cannot be authenticated"):
        journal.inspect()
    with pytest.raises(Conflict, match="never replaces"):
        journal.initialise()


def test_capacity_is_reserved_before_accepting_intent(journal, monkeypatch):
    original = journal.path.read_bytes()
    monkeypatch.setattr(recovery_journal, "MAX_EVENTS", 0)
    with pytest.raises(Conflict, match="full"):
        review(journal)
    monkeypatch.setattr(recovery_journal, "MAX_EVENTS", 1000)
    monkeypatch.setattr(recovery_journal, "MAX_PLAINTEXT", 1200)
    with pytest.raises(Conflict, match="completion capacity"):
        review(journal)
    assert journal.path.read_bytes() == original


def test_ciphertext_and_plaintext_limits(journal, monkeypatch):
    monkeypatch.setattr(recovery_journal, "MAX_CIPHERTEXT", 5)
    with pytest.raises(Conflict, match="safety limit"):
        journal.inspect()
    monkeypatch.setattr(recovery_journal, "MAX_CIPHERTEXT", 10000)
    monkeypatch.setattr(recovery_journal, "MAX_PLAINTEXT", 5)
    with pytest.raises(Conflict, match="safety limit"):
        journal.inspect()


def test_atomic_replace_failure_preserves_history_and_removes_own_temporary(journal, monkeypatch):
    original = journal.path.read_bytes()

    def fail_replace(*args):
        raise OSError("synthetic interrupted replace")

    monkeypatch.setattr(recovery_files.os, "replace", fail_replace)
    with pytest.raises(OSError):
        review(journal)
    assert journal.path.read_bytes() == original
    assert not list(journal.path.parent.glob("*.tmp")) and not journal.lock.exists()


def test_stable_lock_is_never_stolen(journal):
    recovery_files.create_private(journal.lock, b"another writer")
    with pytest.raises(Conflict, match="locked"):
        journal.inspect()
    assert journal.lock.read_bytes() == b"another writer"


@pytest.mark.parametrize(
    "path_kind",
    ["relative", "parent", "directory", "missing_parent", "same_key", "lock_key", "excluded"],
)
def test_reject_unsafe_paths(journal, path_kind):
    path, key = journal.path, journal.key
    excluded = ()
    if path_kind == "relative":
        path = type(path)("relative")
    elif path_kind == "parent":
        path = path.parent / ".." / path.name
    elif path_kind == "directory":
        path = path.parent
    elif path_kind == "missing_parent":
        path = path.parent / "missing" / "journal"
    elif path_kind == "same_key":
        key = path
    elif path_kind == "lock_key":
        key = journal.lock
    else:
        excluded = (path.parent,)
    with pytest.raises(Conflict):
        FileRecoveryJournal(path, key, excluded=excluded)


@pytest.mark.parametrize(
    "field,value", [("restriction", "unknown"), ("target", "11111111-1111-4111-8111-111111111111")]
)
def test_restriction_is_typed_without_arbitrary_personal_details(field, value):
    values = {
        "owner": uuid4(),
        "restriction": "email_opt_out",
        "purpose": "rights_request",
        "due": NOW,
    }
    values[field] = value
    with pytest.raises(ValidationError):
        Restriction.model_validate(values)


@pytest.mark.parametrize("category,count", [("scheduled", 2), ("release", 1), ("mailbox", None)])
def test_copy_review_requires_real_policy_and_respects_existing_minimum(category, count):
    with pytest.raises(ValidationError):
        CopyReview(
            reference=uuid4(), category=category, purpose="quarterly", due=NOW, keep_count=count
        )


def test_scope_and_due_date_validation(journal):
    with pytest.raises(ValidationError):
        journal.record(
            uuid4(),
            Restriction(
                owner=uuid4(),
                restriction="subscription_opt_out",
                purpose="rights_request",
                due=NOW,
            ),
            NOW,
        )
    with pytest.raises(ValidationError, match="ninety days"):
        journal.record(
            uuid4(),
            Restriction(
                owner=uuid4(),
                restriction="objection",
                purpose="rights_request",
                due=NOW,
            ),
            NOW,
        )
    assert journal.inspect()["events"] == []


def test_journal_identifier_is_stable_and_different_from_event(journal):
    identifier = UUID(journal.inspect()["journal_id"])
    event = review(journal)
    journal.complete(event)
    assert UUID(journal.inspect()["journal_id"]) == identifier != event
