"""Retained immutable research may cite evidence from a different saved report."""

from datetime import timedelta
from uuid import UUID, uuid4

import pytest

from ase.adapters.persistence.private_removal_references import _linked
from ase.domain.private_removal import RemovalRequest, RemovalScope
from forecast_lifecycle_helpers import later_observation
from helpers import USER_PASSWORD, bearer, login_token
from private_removal_helpers import authorise, preview
from test_forecast_lifecycle_api import create_forecast


async def test_later_report_used_for_forecast_resolution_cannot_be_removed(
    client, container, user, admin
):
    _, path, _, ledger, _ = await create_forecast(client, container, user)
    container.clock.advance(timedelta(days=3))
    evidence = await later_observation(container, user)
    response = await client.post(
        path + "/" + ledger["anchor"]["id"] + "/reviews",
        headers=bearer(await login_token(client, user.email, USER_PASSWORD)),
        json={
            "state": "resolved",
            "outcome": True,
            "reason": "Observed later evidence.",
            "outcome_evidence": [evidence],
        },
    )
    assert response.status_code == 200, response.text
    await authorise(container, admin, user)
    plan = await preview(
        container, admin, RemovalRequest(user.id, RemovalScope.REPORT, UUID(evidence["report_id"]))
    )
    assert "retained_structured_reference" in plan.blockers


@pytest.mark.parametrize(
    "key", ["evidence", "supporting", "contrary", "passage", "source_reference", "observation"]
)
def test_all_ledger_passage_paths_require_retaining_their_report_versions(key):
    identifier = uuid4()
    passage = {"report_version_id": str(identifier), "evidence_id": "E1", "passage_id": "test"}
    value = [passage] if key in {"evidence", "supporting", "contrary"} else passage
    if key == "observation":
        value = {"passage": passage}
    assert _linked("report_ledger_entries", {key: value}, {identifier})
    assert not _linked("report_ledger_entries", {"reason": str(identifier)}, {identifier})


@pytest.mark.parametrize(
    "value", [{"evidence": "corrupt"}, {"passage": []}, {"evidence": [{"report_version_id": 3}]}]
)
def test_malformed_ledger_reference_is_not_assumed_unlinked(value):
    with pytest.raises(ValueError):
        _linked("report_ledger_entries", value, {uuid4()})


@pytest.mark.parametrize(
    "source,path",
    [
        ("report_jobs", "private_inputs"),
        ("source_review_revisions", "target"),
        ("schedules", "baseline_report_id"),
        ("subscription_revisions", "brief_ref"),
        ("report_versions", "brief_reference"),
        ("report_ledger_entries", "report_version_id"),
    ],
)
def test_saved_structured_reference_formats_are_checked(source, path):
    identifier = uuid4()
    payload = {path: {"id": str(identifier)}}
    if path == "private_inputs":
        payload = {
            "input": {"private_inputs": [{"kind": "durable_report", "report_id": str(identifier)}]}
        }
    elif path == "target":
        payload = {path: {"report_version_id": str(identifier)}}
    elif path.endswith("_id"):
        payload = {path: str(identifier)}
    assert _linked(source, payload, {identifier})
    assert not _linked(source, payload, {uuid4()})


@pytest.mark.parametrize(
    "source,payload",
    [
        ("reports", []),
        ("reports", {"plan_id": 3}),
        ("report_jobs", {"input": {"private_inputs": {}}}),
        ("report_jobs", {"input": {"private_inputs": [None]}}),
        ("assistant_conversations", {"turns": {}}),
        ("source_review_revisions", "unreadable-json"),
    ],
)
def test_corrupt_reference_snapshots_never_allow_a_silent_unlinked_assumption(source, payload):
    with pytest.raises(ValueError):
        _linked(source, payload, {uuid4()})
