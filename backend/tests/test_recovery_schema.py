"""Authenticated but incompatible histories are refused, never silently interpreted."""

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet

from ase.domain.errors import Conflict
from ase.domain.private_removal import RemovalRequest, RemovalScope
from recovery_helpers import journal as journal  # noqa: PLC0414


@pytest.mark.parametrize(
    "fault",
    [
        "invalid_scope",
        "manual_committed",
        "not_applied_without_evidence",
        "pending_with_resolution",
        "duplicate_id",
        "multiple_pending",
    ],
)
def test_impossible_record_states_are_rejected(journal, fault):
    now = datetime.now(UTC)
    journal.begin_removal(uuid4(), RemovalRequest(uuid4(), RemovalScope.ACCOUNT), now)
    cipher = Fernet(journal.key.read_bytes())
    data = json.loads(cipher.decrypt(journal.path.read_bytes()))
    entry = data["entries"][0]
    if fault == "invalid_scope":
        entry["action"]["scope"] = "report"
    elif fault == "manual_committed":
        entry["action"] = {
            "kind": "restriction",
            "owner": str(uuid4()),
            "restriction": "objection",
            "purpose": "rights_request",
            "due": (now + timedelta(days=90)).isoformat(),
        }
        entry["status"] = "committed"
    elif fault == "not_applied_without_evidence":
        entry["status"] = "not_applied"
    elif fault == "pending_with_resolution":
        entry["resolution"] = {
            "operator": str(uuid4()),
            "at": now.isoformat(),
            "evidence_sha256": "a" * 64,
        }
    else:
        other = {**entry, "sequence": 2}
        if fault == "multiple_pending":
            other["id"] = str(uuid4())
        data["entries"].append(other)
    journal.path.write_bytes(cipher.encrypt(json.dumps(data).encode()))
    with pytest.raises(Conflict, match="cannot be authenticated or read"):
        journal.inspect()
